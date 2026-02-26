"""
CryptoSense Validation Module
==============================
Input validation and output sanitization for security.
"""

import re
from typing import Tuple, Optional


# -----------------------------
# Blocked Patterns (Security)
# -----------------------------

BLOCKED_INPUT_PATTERNS = [
    r'<script.*?>.*?</script>',     # XSS script tags
    r'javascript:',                   # JavaScript injection
    r'on\w+\s*=',                     # Event handlers
    r'\{\{.*?\}\}',                   # Template injection
    r'\$\{.*?\}',                     # Template literals
    r'exec\s*\(',                     # Code execution
    r'eval\s*\(',                     # Code evaluation
    r'__import__',                    # Python import injection
    r'os\.system',                    # System calls
    r'subprocess',                    # Subprocess calls
    r'DROP\s+TABLE',                  # SQL injection
    r'DELETE\s+FROM',                 # SQL injection
    r'INSERT\s+INTO',                 # SQL injection
    r'UPDATE\s+.*SET',                # SQL injection
    r'UNION\s+SELECT',                # SQL injection
    r';\s*--',                        # SQL comment
]

BLOCKED_OUTPUT_PATTERNS = [
    r'<script.*?>.*?</script>',       # XSS in output
    r'javascript:',                    # JS in output
    r'data:text/html',                 # Data URL injection
]

# Allowed crypto-related terms
ALLOWED_TOPICS = [
    'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'cardano', 'ada',
    'ripple', 'xrp', 'dogecoin', 'doge', 'polkadot', 'dot', 'chainlink', 'link',
    'avalanche', 'avax', 'polygon', 'matic', 'litecoin', 'ltc', 'shiba', 'shib',
    'crypto', 'cryptocurrency', 'blockchain', 'defi', 'nft', 'token', 'coin',
    'price', 'market', 'trading', 'news', 'trending', 'analysis', 'chart',
    'volume', 'cap', 'supply', 'wallet', 'exchange', 'mining', 'staking',
    'bull', 'bear', 'hodl', 'altcoin', 'uniswap', 'binance', 'coinbase'
]


# -----------------------------
# Validation Functions
# -----------------------------

def validate_input(query: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate user input query.
    
    Args:
        query: User's input query
        
    Returns:
        Tuple of (is_valid, sanitized_query, error_message)
    """
    if not query or not isinstance(query, str):
        return False, "", "Query cannot be empty."
    
    # Strip and limit length
    query = query.strip()
    
    if len(query) < 2:
        return False, "", "Query is too short. Please provide more details."
    
    if len(query) > 500:
        return False, "", "Query is too long. Please limit to 500 characters."
    
    # Check for blocked patterns
    query_lower = query.lower()
    for pattern in BLOCKED_INPUT_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return False, "", "Invalid query detected. Please enter a valid cryptocurrency question."
    
    # Check for at least one crypto-related term (optional soft validation)
    has_crypto_term = any(term in query_lower for term in ALLOWED_TOPICS)
    
    if not has_crypto_term:
        # Allow but warn - query might still be valid
        pass  # Soft validation - orchestrator will handle intent
    
    # Sanitize - remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', query)
    sanitized = sanitized.strip()
    
    return True, sanitized, None


def validate_output(response: str) -> Tuple[bool, str]:
    """
    Validate and sanitize LLM output.
    
    Args:
        response: LLM's output response
        
    Returns:
        Tuple of (is_valid, sanitized_response)
    """
    if not response or not isinstance(response, str):
        return True, "No response generated."
    
    # Check for blocked patterns in output
    for pattern in BLOCKED_OUTPUT_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            response = re.sub(pattern, '[REMOVED]', response, flags=re.IGNORECASE)
    
    # Remove any potential HTML/script injection
    response = re.sub(r'<[^>]+>', '', response)
    
    # Limit response length
    if len(response) > 10000:
        response = response[:10000] + "\n\n[Response truncated for safety]"
    
    return True, response


def sanitize_coin_id(coin_id: str) -> str:
    """
    Sanitize coin ID input.
    
    Args:
        coin_id: Coin identifier
        
    Returns:
        Sanitized coin ID
    """
    if not coin_id:
        return "bitcoin"
    
    # Only allow alphanumeric, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', coin_id.lower().strip())
    
    # Limit length
    return sanitized[:50] if sanitized else "bitcoin"


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe."""
    if not url:
        return False
    
    safe_domains = [
        'coingecko.com',
        'coindesk.com',
        'wikipedia.org',
        'wikimedia.org'
    ]
    
    return any(domain in url.lower() for domain in safe_domains)


# -----------------------------
# Rate Limiting (Simple)
# -----------------------------

class SimpleRateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        import time
        current_time = time.time()
        
        # Remove old requests
        self.requests = [t for t in self.requests if current_time - t < self.window_seconds]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(current_time)
        return True
    
    def get_wait_time(self) -> int:
        """Get seconds to wait before next request."""
        if not self.requests:
            return 0
        
        import time
        oldest = min(self.requests)
        wait = self.window_seconds - (time.time() - oldest)
        return max(0, int(wait))


# Global rate limiter instance
rate_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)
