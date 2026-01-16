"""
Helper functions for detecting request source type (workbench vs API)
"""

from fastapi import Request


def detect_source_type(request: Request) -> str:
    """
    Detect if request came from workbench or API.

    Strategies:
    1. Check for JWT token (workbench) vs Basic Auth (API)
    2. Check User-Agent header
    3. Check Referer header
    4. Default to 'api' if uncertain
    """
    auth_header = request.headers.get('Authorization', '')

    # JWT token indicates workbench
    if auth_header.startswith('Bearer '):
        return 'workbench'

    # Basic auth indicates API
    if auth_header.startswith('Basic '):
        return 'api'

    # Check User-Agent for browser patterns
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(browser in user_agent for browser in ['mozilla', 'chrome', 'safari', 'firefox']):
        return 'workbench'

    # Check if request came from the dashboard
    referer = request.headers.get('Referer', '')
    if referer and '/dashboard' in referer:
        return 'workbench'

    # Default to API
    return 'api'