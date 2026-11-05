"""
Security and SSRF Protection Module for IOL.
Guards outbound network operations against SSRF, DNS rebinding, private IP probing,
cloud metadata access (169.254.169.254), and memory exhaustion attacks.
"""

import ipaddress
import logging
import socket
import urllib.parse
from typing import Any, Dict, Optional, Tuple
import requests

logger = logging.getLogger("iol.security")

# Maximum content size accepted from live external HTTP queries (2MB)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024

# Cloud metadata and internal service IP addresses to strictly prohibit
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "instance-data",
    "kubernetes.default.svc",
    "169.254.169.254",
    "fd00:ec2::254"
}


class SSRFSecurityError(ValueError):
    """Raised when an outbound URL points to an internal, private, or prohibited destination."""
    pass


def validate_url_safety(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validates whether an external URL is safe to retrieve.
    Blocks:
    - Non-HTTP/HTTPS schemes (file://, gopher://, ftp://, dict://)
    - Loopback IPs (127.0.0.0/8, ::1)
    - IPv4-mapped IPv6 loopbacks (::ffff:127.0.0.1)
    - Private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7)
    - Link-local and cloud metadata IPs (169.254.0.0/16, fe80::/10, 169.254.169.254)
    - Multicast and reserved blocks
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        return False, f"Malformed URL syntax: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL contains no valid host or domain name."

    hostname_lower = hostname.lower()
    if (
        hostname_lower in BLOCKED_HOSTNAMES
        or hostname_lower.endswith(".local")
        or hostname_lower.endswith(".internal")
        or hostname_lower.endswith(".localhost")
    ):
        return False, f"Host '{hostname}' is explicitly blocked (internal/metadata domain)."

    # Resolve IP address to detect DNS rebinding, loopbacks, and private aliases
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            # Explicit check for cloud metadata
            if ip_str == "169.254.169.254" or str(ip_obj) == "169.254.169.254":
                return False, "Access to cloud metadata service (169.254.169.254) is strictly prohibited."

            if ip_obj.is_loopback:
                return False, f"Resolution to loopback address '{ip_str}' is prohibited."
            if ip_obj.is_private:
                return False, f"Resolution to private network IP '{ip_str}' is prohibited."
            if ip_obj.is_link_local:
                return False, f"Resolution to link-local IP '{ip_str}' is prohibited."
            if ip_obj.is_reserved:
                return False, f"Resolution to reserved address block '{ip_str}' is prohibited."
            if ip_obj.is_multicast:
                return False, f"Resolution to multicast address '{ip_str}' is prohibited."

            # Check IPv4-mapped IPv6 address (e.g. ::ffff:127.0.0.1 or ::ffff:10.0.0.1)
            if ip_obj.version == 6 and ip_obj.ipv4_mapped:
                mapped = ip_obj.ipv4_mapped
                if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_reserved:
                    return False, f"Resolution to IPv4-mapped private IP '{mapped}' is prohibited."
    except socket.gaierror as e:
        logger.debug(f"Host '{hostname}' could not be resolved during safety pre-check: {e}")
    except Exception as e:
        return False, f"DNS resolution safety check failed: {e}"

    return True, None


def safe_http_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 4.0,
    max_bytes: int = MAX_RESPONSE_BYTES,
    max_redirects: int = 3
) -> Optional[requests.Response]:
    """
    Safely executes an outbound HTTP GET request with SSRF guard, redirect inspection, and response limit.
    Follows redirects safely with explicit validation on every hop.
    """
    default_headers = {
        "User-Agent": "Intent-Operating-Layer/0.4.0 (Security-Guarded Research Agent; mailto:iol-research@bitverse.org)"
    }
    if headers:
        default_headers.update(headers)

    curr_url = url
    redirect_count = 0
    resp: Optional[requests.Response] = None

    while redirect_count <= max_redirects:
        # Validate current URL before issuing request
        is_safe, reason = validate_url_safety(curr_url)
        if not is_safe:
            logger.warning(f"SSRF violation blocked request to '{curr_url}': {reason}")
            raise SSRFSecurityError(f"Security boundary blocked outbound request: {reason}")

        # Request with allow_redirects=False to inspect redirect destinations
        resp = requests.get(
            curr_url,
            headers=default_headers,
            timeout=timeout,
            allow_redirects=False,
            stream=True
        )

        # Check if response is a redirection
        if resp.status_code in (301, 302, 303, 307, 308):
            redirect_target = resp.headers.get("Location")
            if not redirect_target:
                break
            # Compute absolute target
            curr_url = urllib.parse.urljoin(curr_url, redirect_target)
            redirect_count += 1
            continue

        # Normal response reached
        break

    if redirect_count > max_redirects:
        raise SSRFSecurityError(f"Exceeded maximum allowed redirects ({max_redirects}).")

    if resp is None:
        return None

    # Stream content up to max_bytes to avoid memory exhaustion attacks
    chunks = []
    total_bytes = 0
    for chunk in resp.iter_content(chunk_size=16384):
        if not chunk:
            continue
        chunks.append(chunk)
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            logger.warning(f"Response from '{curr_url}' exceeded max allowed size of {max_bytes} bytes. Truncating.")
            break

    resp._content = b"".join(chunks)[:max_bytes]
    return resp


def sanitize_extracted_string(text: Any, max_len: int = 500) -> str:
    """Sanitize strings extracted from raw HTML/API to prevent control code leakage."""
    if text is None:
        return ""
    import re
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(text))
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:max_len]
