import hashlib
import os
import re
import tempfile
from urllib.parse import urlparse

import requests

from .config import load_settings
from .url_security import (
    MAX_REDIRECTS,
    normalize_and_validate_url,
    validated_redirect_url,
)

MAX_MEDIA_BYTES = 10 * 1024 * 1024
IMAGE_CONTENT_RE = re.compile(r"^image/")


def target_media_hash(target):
    return hashlib.sha256(target.encode("utf-8")).hexdigest()[:32]


def make_target_media_dir(target):
    settings = load_settings(require_secret=False)
    target_dir = os.path.join(settings.media_dir, target_media_hash(target))
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def normalize_filename(url):
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        name = "media"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if len(name) > 128:
        name = name[-128:]
    return name


def compute_checksum(data):
    sha = hashlib.sha256()
    sha.update(data)
    return sha.hexdigest()


def request_kwargs():
    settings = load_settings(require_secret=False)
    kwargs = {
        "stream": True,
        "timeout": 20,
        "headers": {"User-Agent": "SOCMINT-Media-Downloader/1.0"},
    }
    if settings.tor_proxy:
        kwargs["proxies"] = {"http": settings.tor_proxy, "https": settings.tor_proxy}
    return kwargs


def download_media(target, url):
    settings = load_settings(require_secret=False)
    url = normalize_and_validate_url(url, allow_onion=bool(settings.tor_proxy))
    if not url:
        return None

    try:
        kwargs = request_kwargs()
        kwargs["allow_redirects"] = False
        response = None
        for _ in range(MAX_REDIRECTS + 1):
            response = requests.get(url, **kwargs)
            if not response.is_redirect:
                break
            next_url = validated_redirect_url(
                url,
                response.headers.get("Location"),
                allow_onion=bool(settings.tor_proxy),
            )
            response.close()
            if not next_url:
                return None
            url = next_url
        if response is not None and response.is_redirect:
            response.close()
            return None
        response.raise_for_status()
    except Exception:
        return None

    content_type = response.headers.get("Content-Type", "")
    if not IMAGE_CONTENT_RE.match(content_type):
        return None

    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_MEDIA_BYTES:
                return None
        except ValueError:
            pass

    target_dir = make_target_media_dir(target)
    filename = normalize_filename(url)
    path = os.path.abspath(os.path.join(target_dir, filename))
    if not path.startswith(os.path.abspath(target_dir) + os.sep):
        return None
    if os.path.exists(path):
        with open(path, "rb") as existing_file:
            checksum = compute_checksum(existing_file.read())
        return {
            "target": target,
            "url": url,
            "path": path,
            "checksum": checksum,
            "status": "exists",
            "content_type": content_type,
        }

    size_bytes = 0
    sha = hashlib.sha256()
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=target_dir)
    temp_path = temp_file.name
    try:
        with temp_file:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                size_bytes += len(chunk)
                if size_bytes > MAX_MEDIA_BYTES:
                    return None
                sha.update(chunk)
                temp_file.write(chunk)
        os.replace(temp_path, path)
    finally:
        response.close()
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    checksum = sha.hexdigest()
    return {
        "target": target,
        "url": url,
        "path": path,
        "checksum": checksum,
        "status": "downloaded",
        "content_type": content_type,
        "size_bytes": size_bytes,
    }
