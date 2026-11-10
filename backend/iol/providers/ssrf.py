"""
Server-Side Request Forgery (SSRF) and Network Boundary Protection.
Guarantees that model provider URLs are restricted to authorized cloud APIs
and explicitly verified local model runtime endpoints.
Prevents internal network port scanning, AWS/GCP metadata interception,
and unauthorized access to loopback services (such as IOL API or database ports).
"""

import ipaddress
import re
import socket
from typing import Set, Tuple
from urllib.parse import urlparse

# Explicitly authorized cloud foundation model domains
AUTHORIZED_CLOUD_DOMAINS: Set[str] = {
    "generativelanguage.googleapis.com",
    "api.openai.com",
    "api.anthropic.com",
    "openai.azure.com",
}

# Explicitly authorized loopback ports for local model inference runtimes
AUTHORIZED_LOCAL_MODEL_PORTS: Set[int] = {
    11434,  # Ollama daemon
    18080,  # llama.cpp / llama-server alternate
    8080,   # llama.cpp / llama-server default
    8001,   # vLLM worker
    5000,   # LocalAI default
}

# Strictly forbidden loopback / system ports
FORBIDDEN_LOCAL_PORTS: Set[int] = {
    8000,   # IOL Backend API
    3000,   # IOL Frontend Next.js
    5432,   # PostgreSQL
    6379,   # Redis
    27017,  # MongoDB
    3306,   # MySQL
    22,     # SSH
    23,     # Telnet
    25,     # SMTP
}


class SSRFValidationError(ValueError):
    """Raised when an endpoint URL violates SSRF security boundaries."""
    pass


def validate_provider_endpoint(url: str, allow_custom_cloud: bool = False) -> Tuple[bool, str]:
    """
    Validates a provider endpoint URL against strict SSRF security rules.
    Returns (is_valid, sanitized_or_reason).
    """
    if not url or not isinstance(url, str):
        return False, "Endpoint URL is empty or invalid"

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    # 1. Scheme enforcement
    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'; only http and https are permitted"

    # 2. Reject credentials in URL (user:pass@host)
    if parsed.username or parsed.password:
        return False, "Embedded credentials in endpoint URL are forbidden"

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in endpoint URL"

    hostname_lower = hostname.lower()

    # 3. Cloud Metadata IP protection
    if hostname_lower in ("169.254.169.254", "metadata.google.internal", "instance-data"):
        return False, "Access to cloud instance metadata services is strictly forbidden"

    # 4. Loopback / Localhost validation
    is_loopback = (
        hostname_lower in ("127.0.0.1", "localhost", "::1", "0.0.0.0")
        or hostname_lower.endswith(".localhost")
    )

    # Check IP addresses directly
    try:
        ip = ipaddress.ip_address(hostname_lower)
        if ip.is_loopback or ip.is_unspecified:
            is_loopback = True
        elif ip.is_link_local or ip.is_multicast:
            return False, f"Access to link-local/multicast IP {ip} is forbidden"
        elif ip.is_private and not allow_custom_cloud:
            # Private network range (e.g. 10.x, 192.168.x, 172.16-31.x)
            return False, f"Access to private intranet IP {ip} is forbidden without explicit network policy"
    except ValueError:
        # Not a raw IP literal; hostname string
        pass

    if is_loopback:
        port = parsed.port
        if not port:
            # Default http=80, https=443 on localhost is forbidden
            return False, "Loopback endpoint must specify an authorized model service port (e.g. 11434)"

        if port in FORBIDDEN_LOCAL_PORTS:
            return False, f"Access to system port {port} on loopback is strictly prohibited"

        if port not in AUTHORIZED_LOCAL_MODEL_PORTS:
            return False, f"Port {port} is not an authorized local model runtime port (allowed: {sorted(AUTHORIZED_LOCAL_MODEL_PORTS)})"

        return True, "Authorized local model runtime endpoint"

    # 5. Cloud Endpoint Validation
    if parsed.scheme != "https" and not is_loopback:
        return False, "External cloud provider endpoints must use HTTPS"

    # Check against known authorized cloud domains
    is_known_cloud = any(
        hostname_lower == d or hostname_lower.endswith(f".{d}")
        for d in AUTHORIZED_CLOUD_DOMAINS
    )

    if is_known_cloud:
        return True, "Authorized cloud foundation model endpoint"

    if allow_custom_cloud:
        # Custom domain allowed provided it is not private IP
        try:
            resolved_ip = socket.gethostbyname(hostname_lower)
            rip = ipaddress.ip_address(resolved_ip)
            if rip.is_loopback or rip.is_private or rip.is_link_local or rip.is_unspecified:
                return False, f"Custom cloud domain {hostname_lower} resolves to forbidden internal IP {rip}"
        except Exception:
            pass
        return True, "Custom verified cloud endpoint"

    return False, f"Cloud domain '{hostname_lower}' is not an authorized foundation model provider domain"
