"""
CryptoSense Voice Agent
========================
Speech-to-Text (STT) and Text-to-Speech (TTS) powered by Groq Cloud.

STT Model: whisper-large-v3  (Groq audio transcription endpoint)
TTS Model: canopylabs/orpheus-v1-english  (Groq audio speech endpoint)

Flow:
  User speaks → Whisper transcribes → MCP query → Orpheus speaks response
"""

import os
import time
import tempfile
import logging
import asyncio
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

import edge_tts

load_dotenv()

logger = logging.getLogger("CryptoSense.VoiceAgent")

# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

STT_MODEL = "whisper-large-v3"
# TTS_MODEL = "canopylabs/orpheus-v1-english" # Disabled due to Terms prompt
TTS_MODEL = "edge-tts" # Using free edge-tts instead

AVAILABLE_VOICES = ["tara", "leah", "jess", "leo", "dan", "mia"]
EDGE_VOICE_MAP = {
    "tara": "en-US-AriaNeural",
    "leah": "en-US-JennyNeural",
    "jess": "en-GB-SoniaNeural",
    "leo": "en-US-GuyNeural",
    "dan": "en-GB-RyanNeural",
    "mia": "en-AU-NatashaNeural"
}
DEFAULT_VOICE = "tara"

# Max characters to send to TTS (Orpheus has throughput limits)
TTS_MAX_CHARS = 2000

# Temp directory for generated audio files
VOICE_TEMP_DIR = os.path.join(tempfile.gettempdir(), "cryptosense_voice")
os.makedirs(VOICE_TEMP_DIR, exist_ok=True)


def _get_groq_client():
    """Initialize Groq client with API key."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env file")
    return Groq(api_key=api_key)


# ──────────────────────────────────────────────
#  Speech-to-Text (STT) — Whisper Large V3
# ──────────────────────────────────────────────


def transcribe_audio(audio_filepath: str) -> str:
    """
    Transcribe an audio file to text using Groq's Whisper Large V3.

    Args:
        audio_filepath: Path to audio file (WAV, MP3, WEBM, etc.)

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If no audio file provided or API key missing.
        Exception: On transcription API failure.
    """
    if not audio_filepath or not os.path.exists(audio_filepath):
        raise ValueError("No audio file provided or file does not exist.")

    file_size = os.path.getsize(audio_filepath)
    if file_size == 0:
        raise ValueError("Audio file is empty — please record something first.")

    logger.info(f"Transcribing audio: {audio_filepath} ({file_size} bytes)")
    start = time.time()

    client = _get_groq_client()

    with open(audio_filepath, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_filepath), audio_file),
            model=STT_MODEL,
            response_format="text",
            language="en",
        )

    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(f"Transcription complete in {elapsed}ms: {transcription[:80]}...")

    # The response_format="text" returns a plain string
    text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()

    if not text:
        raise ValueError("Transcription returned empty — audio may be too short or silent.")

    return text


# ──────────────────────────────────────────────
#  Text-to-Speech (TTS) — Free Edge TTS
# ──────────────────────────────────────────────


def _prepare_tts_text(report: str) -> str:
    """
    Prepare report text for TTS — extract a spoken summary.

    Strips formatting characters and truncates to TTS_MAX_CHARS.
    Adds natural phrasing for better speech output.
    """
    if not report:
        return "No report was generated."

    # Remove heavy formatting characters that don't sound good when spoken
    cleanup_chars = ["═", "━", "─", "│", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼"]
    text = report
    for ch in cleanup_chars:
        text = text.replace(ch, "")

    # Remove emoji-heavy prefixes for cleaner speech
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are only formatting
        if all(c in " -=_*#" for c in stripped):
            continue
        clean_lines.append(stripped)

    text = ". ".join(clean_lines)

    # Truncate if too long
    if len(text) > TTS_MAX_CHARS:
        # Try to cut at a sentence boundary
        truncated = text[:TTS_MAX_CHARS]
        last_period = truncated.rfind(".")
        if last_period > TTS_MAX_CHARS // 2:
            text = truncated[: last_period + 1]
        else:
            text = truncated + "..."

    return text


def text_to_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
) -> str:
    """
    Convert text to speech using free Microsoft Edge TTS.

    Args:
        text: Text to convert to speech.
        voice: Voice persona mapping.

    Returns:
        Path to the generated MP3 audio file.

    Raises:
        ValueError: If text is empty or voice is invalid.
        Exception: On TTS API failure.
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate speech from empty text.")

    if voice not in AVAILABLE_VOICES:
        logger.warning(f"Invalid voice '{voice}', falling back to '{DEFAULT_VOICE}'")
        voice = DEFAULT_VOICE

    edge_voice = EDGE_VOICE_MAP.get(voice, "en-US-AriaNeural")

    # Prepare text for speech
    spoken_text = _prepare_tts_text(text)

    logger.info(f"Generating Edge TTS with voice='{edge_voice}', text_len={len(spoken_text)}")
    start = time.time()

    # Save to temp file as MP3 (default for edge-tts)
    output_path = os.path.join(
        VOICE_TEMP_DIR,
        f"cryptosense_tts_{int(time.time())}.mp3",
    )

    async def _generate():
        communicate = edge_tts.Communicate(spoken_text, edge_voice)
        await communicate.save(output_path)

    try:
        # Check if an event loop is already running in this thread
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop, so use standard run
        asyncio.run(_generate())
    else:
        # We are inside an event loop (e.g. Gradio worker)
        # Create a new task within the current asyncio loop
        future = asyncio.run_coroutine_threadsafe(_generate(), loop)
        future.result()  # Wait for it to finish

    elapsed = round((time.time() - start) * 1000, 2)
    file_size = os.path.getsize(output_path)
    logger.info(f"TTS complete in {elapsed}ms → {output_path} ({file_size} bytes)")

    return output_path


# ──────────────────────────────────────────────
#  Full Voice Pipeline
# ──────────────────────────────────────────────


def process_voice_query(
    audio_input,
    voice: str = DEFAULT_VOICE,
) -> Tuple[str, str, Optional[str], str]:
    """
    Full voice pipeline: STT → MCP Query → TTS.

    Args:
        audio_input: Audio filepath from Gradio microphone component.
        voice: TTS voice persona.

    Returns:
        Tuple of (transcription, report, audio_path, eval_metrics)
    """
    from mcp_client import run_query, check_server
    from validation import validate_input, validate_output, rate_limiter
    from evaluation import evaluator, evaluation_store
    from monitoring import metrics_store

    # ── Step 0: Validate audio input ──
    if audio_input is None:
        return (
            "",
            "🎤 **No audio recorded.** Please click the microphone and speak your query.",
            None,
            "",
        )

    # Handle Gradio audio format — can be filepath string or tuple(sr, data)
    if isinstance(audio_input, tuple):
        # Gradio sometimes returns (sample_rate, numpy_array) — save to temp WAV
        import numpy as np
        import wave

        sr, data = audio_input
        temp_wav = os.path.join(VOICE_TEMP_DIR, f"mic_input_{int(time.time())}.wav")
        with wave.open(temp_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            if isinstance(data, np.ndarray):
                if data.dtype != np.int16:
                    data = (data * 32767).astype(np.int16)
                wf.writeframes(data.tobytes())
        audio_filepath = temp_wav
    else:
        audio_filepath = audio_input

    # ── Step 1: Speech-to-Text ──
    try:
        transcription = transcribe_audio(audio_filepath)
    except ValueError as e:
        return (str(e), "", None, "")
    except Exception as e:
        return (f"❌ STT Error: {str(e)}", "", None, "")

    # ── Step 2: Check MCP Server ──
    if not check_server():
        return (
            transcription,
            "❌ **MCP Server is not running!**\n\nStart the server first:\n```\npython mcp_server.py --transport sse\n```",
            None,
            "",
        )

    # ── Step 3: Rate limiting & validation ──
    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.get_wait_time()
        return (
            transcription,
            f"⏳ Rate limit reached. Please wait {wait_time} seconds.",
            None,
            "",
        )

    is_valid, sanitized_query, error = validate_input(transcription)
    if not is_valid:
        return (transcription, f"❌ {error}", None, "")

    # ── Step 4: Run query via MCP pipeline ──
    try:
        result = run_query(sanitized_query)
        report = result.get("report", "No report generated.")
        mcp_metrics = result.get("metrics", {})

        # Output validation
        _, sanitized_report = validate_output(report)

        # ── Step 5: Evaluation ──
        eval_metrics = {
            "total_latency_ms": mcp_metrics.get("total_latency_ms", 0),
            "llm_calls": mcp_metrics.get("llm_calls", 0),
            "total_tokens": mcp_metrics.get("total_tokens", 0),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "tool_calls": mcp_metrics.get("tool_calls", 0),
            "tool_errors": mcp_metrics.get("tool_errors", 0),
            "steps": mcp_metrics.get("llm_calls", 0) + mcp_metrics.get("tool_calls", 0),
            "agents_invoked": ["mcp-client", "voice-agent"],
            "tools_invoked": mcp_metrics.get("tools_invoked", []),
            "errors": [
                t["error"]
                for t in mcp_metrics.get("tool_details", [])
                if t.get("error")
            ],
        }

        eval_report = evaluator.evaluate(
            query=sanitized_query,
            final_report=sanitized_report,
            metrics=eval_metrics,
            coin_id="",
            tasks=None,
        )
        evaluation_store.record(eval_report)
        metrics_store.record(
            sanitized_query, eval_metrics, report_preview=sanitized_report[:200]
        )

        # Build eval display
        eval_data = eval_report.to_dict()
        lines = []
        lines.append("═" * 50)
        lines.append("   🎙️ VOICE QUERY — METRICS & EVALUATION")
        lines.append("═" * 50)
        lines.append(
            f"\n⏱  Latency:          {mcp_metrics.get('total_latency_ms', 0):.0f} ms"
        )
        lines.append(f"🤖 LLM Calls:        {mcp_metrics.get('llm_calls', 0)}")
        lines.append(f"🔧 Tool Calls:       {mcp_metrics.get('tool_calls', 0)}")
        lines.append(f"🎯 Tokens:           {mcp_metrics.get('total_tokens', 0)}")

        overall = eval_data.get("overall_score", 0)
        passed = eval_data.get("passed", False)
        lines.append(f"\n{'─' * 50}")
        lines.append(
            f"Overall Score:       {overall:.2%}  {'✅ PASSED' if passed else '❌ FAILED'}"
        )
        lines.append("═" * 50)
        eval_display = "\n".join(lines)

    except Exception as e:
        return (transcription, f"❌ Query Error: {str(e)}", None, "")

    # ── Step 6: Text-to-Speech ──
    audio_path = None
    try:
        audio_path = text_to_speech(sanitized_report, voice=voice)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        # Non-fatal — still return the text report
        eval_display += f"\n⚠️ TTS Error: {str(e)}"

    return (transcription, sanitized_report, audio_path, eval_display)


def process_text_with_voice(
    query: str,
    voice: str = DEFAULT_VOICE,
) -> Tuple[str, Optional[str], str]:
    """
    Process a typed text query and return both text report + TTS audio.

    Used for quick-action buttons in voice tab that bypass microphone.

    Args:
        query: Text query string.
        voice: TTS voice persona.

    Returns:
        Tuple of (report, audio_path, eval_metrics)
    """
    from mcp_client import run_query, check_server
    from validation import validate_input, validate_output, rate_limiter
    from evaluation import evaluator, evaluation_store
    from monitoring import metrics_store

    if not check_server():
        return (
            "❌ **MCP Server is not running!**\n\nStart the server first:\n```\npython mcp_server.py --transport sse\n```",
            None,
            "",
        )

    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.get_wait_time()
        return (f"⏳ Rate limit reached. Please wait {wait_time} seconds.", None, "")

    is_valid, sanitized_query, error = validate_input(query)
    if not is_valid:
        return (f"❌ {error}", None, "")

    try:
        result = run_query(sanitized_query)
        report = result.get("report", "No report generated.")
        mcp_metrics = result.get("metrics", {})
        _, sanitized_report = validate_output(report)

        # Evaluation
        eval_metrics = {
            "total_latency_ms": mcp_metrics.get("total_latency_ms", 0),
            "llm_calls": mcp_metrics.get("llm_calls", 0),
            "total_tokens": mcp_metrics.get("total_tokens", 0),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "tool_calls": mcp_metrics.get("tool_calls", 0),
            "tool_errors": mcp_metrics.get("tool_errors", 0),
            "steps": mcp_metrics.get("llm_calls", 0) + mcp_metrics.get("tool_calls", 0),
            "agents_invoked": ["mcp-client", "voice-agent"],
            "tools_invoked": mcp_metrics.get("tools_invoked", []),
            "errors": [
                t["error"]
                for t in mcp_metrics.get("tool_details", [])
                if t.get("error")
            ],
        }

        eval_report = evaluator.evaluate(
            query=sanitized_query,
            final_report=sanitized_report,
            metrics=eval_metrics,
            coin_id="",
            tasks=None,
        )
        evaluation_store.record(eval_report)
        metrics_store.record(
            sanitized_query, eval_metrics, report_preview=sanitized_report[:200]
        )

        eval_data = eval_report.to_dict()
        overall = eval_data.get("overall_score", 0)
        passed = eval_data.get("passed", False)
        eval_display = (
            f"Score: {overall:.2%} {'✅' if passed else '❌'} | "
            f"Latency: {mcp_metrics.get('total_latency_ms', 0):.0f}ms | "
            f"Tools: {mcp_metrics.get('tool_calls', 0)}"
        )

    except Exception as e:
        return (f"❌ Error: {str(e)}", None, "")

    # TTS
    audio_path = None
    try:
        audio_path = text_to_speech(sanitized_report, voice=voice)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        eval_display += f" | ⚠️ TTS Error: {str(e)}"

    return (sanitized_report, audio_path, eval_display)


# ──────────────────────────────────────────────
#  Cleanup utility
# ──────────────────────────────────────────────


def cleanup_old_audio(max_age_seconds: int = 3600):
    """Remove TTS audio files older than max_age_seconds."""
    now = time.time()
    for ext in ["*.wav", "*.mp3"]:
        for f in Path(VOICE_TEMP_DIR).glob(ext):
            if now - f.stat().st_mtime > max_age_seconds:
                try:
                    f.unlink()
                except OSError:
                    pass
