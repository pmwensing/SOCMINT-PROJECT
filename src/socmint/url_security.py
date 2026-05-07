import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urlunparse


BLOCKED_HOSTS = {'localhost', 'localhost.localdomain'}
MAX_REDIRECTS = 3


def host_is_onion(hostname):
    return hostname.lower().endswith('.onion')


def ip_is_blocked(address):
    ip = ipaddress.ip_address(address)
    return any([
        ip.is_private,
        ip.is_loopback,
        ip.is_link_local,
        ip.is_multicast,
        ip.is_reserved,
        ip.is_unspecified,
    ])


def resolve_host_ips(hostname):
    return {
        result[4][0]
        for result in socket.getaddrinfo(hostname, None)
    }


def normalize_and_validate_url(url, allow_onion=False):
    if not url:
        return None

    parsed = urlparse(url.strip())
    if parsed.scheme not in {'http', 'https'}:
        return None
    if not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None

    hostname = parsed.hostname.strip().lower().rstrip('.')
    if hostname in BLOCKED_HOSTS:
        return None

    if host_is_onion(hostname):
        if not allow_onion:
            return None
    else:
        try:
            addresses = resolve_host_ips(hostname)
        except OSError:
            return None
        if not addresses or any(ip_is_blocked(address) for address in addresses):
            return None

    netloc = hostname
    if parsed.port:
        netloc = f'{netloc}:{parsed.port}'
    normalized = parsed._replace(netloc=netloc, fragment='')
    return urlunparse(normalized)


def validated_redirect_url(current_url, location, allow_onion=False):
    if not location:
        return None
    return normalize_and_validate_url(urljoin(current_url, location), allow_onion=allow_onion)
