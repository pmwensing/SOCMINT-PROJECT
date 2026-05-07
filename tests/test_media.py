from pathlib import Path
from unittest.mock import Mock, patch

from src.socmint import media


def test_media_uses_hashed_target_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('SOCMINT_DATA_DIR', str(tmp_path))
    target_dir = Path(media.make_target_media_dir('operator_1'))

    assert target_dir.parent == tmp_path / 'media'
    assert target_dir.name == media.target_media_hash('operator_1')
    assert 'operator_1' not in str(target_dir)


def test_download_media_honors_tor_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv('SOCMINT_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('SOCMINT_TOR_PROXY', 'socks5h://127.0.0.1:9050')
    response = Mock()
    response.is_redirect = False
    response.headers = {'Content-Type': 'image/png', 'Content-Length': '4'}
    response.iter_content.return_value = [b'data']
    response.raise_for_status.return_value = None

    with patch('src.socmint.url_security.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 0))]), \
            patch('src.socmint.media.requests.get', return_value=response) as mock_get:
        result = media.download_media('operator_1', 'https://example.com/image.png')

    assert result['status'] == 'downloaded'
    assert mock_get.call_args.kwargs['proxies'] == {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050',
    }


def test_download_media_rejects_unsafe_url(tmp_path, monkeypatch):
    monkeypatch.setenv('SOCMINT_DATA_DIR', str(tmp_path))

    with patch('src.socmint.media.requests.get') as mock_get:
        assert media.download_media('operator_1', 'http://localhost/image.png') is None

    mock_get.assert_not_called()


def test_download_media_streams_and_rejects_oversized_body(tmp_path, monkeypatch):
    monkeypatch.setenv('SOCMINT_DATA_DIR', str(tmp_path))
    response = Mock()
    response.is_redirect = False
    response.headers = {'Content-Type': 'image/png'}
    response.iter_content.return_value = [b'a' * (media.MAX_MEDIA_BYTES + 1)]
    response.raise_for_status.return_value = None

    with patch('src.socmint.url_security.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 0))]), \
            patch('src.socmint.media.requests.get', return_value=response):
        assert media.download_media('operator_1', 'https://example.com/image.png') is None
