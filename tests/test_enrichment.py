from unittest.mock import patch
from src.socmint.enrichment import parse_tool_output, scrape_profile_url

def test_parse_tool_output():
    raw = '{"key": "value"}'
    parsed = parse_tool_output('test', raw)
    assert parsed['json'] == {"key": "value"}

@patch('src.socmint.enrichment.session.get')
def test_scrape_profile_url(mock_get, monkeypatch):
    monkeypatch.delenv('SOCMINT_TOR_PROXY', raising=False)
    class MockResponse:
        is_redirect = False
        headers = {}
        text = '<html><title>Test</title></html>'
        def raise_for_status(self):
            return None

    mock_get.return_value = MockResponse()
    with patch('src.socmint.url_security.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 0))]):
        result = scrape_profile_url('http://example.com')
    assert result['title'] == 'Test'


@patch('src.socmint.enrichment.session.get')
def test_scrape_profile_url_uses_tor_proxy(mock_get, monkeypatch):
    monkeypatch.setenv('SOCMINT_TOR_PROXY', 'socks5h://127.0.0.1:9050')

    class MockResponse:
        is_redirect = False
        headers = {}
        text = '<html><title>Test</title></html>'
        def raise_for_status(self):
            return None

    mock_get.return_value = MockResponse()
    with patch('src.socmint.url_security.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 0))]):
        scrape_profile_url('http://example.com')
    assert mock_get.call_args.kwargs['proxies'] == {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050',
    }


@patch('src.socmint.enrichment.session.get')
def test_scrape_profile_url_rejects_private_hosts(mock_get):
    assert scrape_profile_url('http://localhost/profile') is None
    mock_get.assert_not_called()
