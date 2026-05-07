from unittest.mock import patch

from src.socmint.url_security import normalize_and_validate_url


def test_rejects_localhost():
    assert normalize_and_validate_url('http://localhost:8000') is None


@patch('src.socmint.url_security.socket.getaddrinfo')
def test_rejects_private_ip_resolution(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(None, None, None, None, ('10.0.0.5', 0))]

    assert normalize_and_validate_url('https://example.com/path') is None


@patch('src.socmint.url_security.socket.getaddrinfo')
def test_normalizes_public_url(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(None, None, None, None, ('93.184.216.34', 0))]

    assert normalize_and_validate_url('https://EXAMPLE.com/path#frag') == 'https://example.com/path'


def test_onion_requires_explicit_allowance():
    assert normalize_and_validate_url('http://example.onion') is None
    assert normalize_and_validate_url('http://example.onion', allow_onion=True) == 'http://example.onion'
