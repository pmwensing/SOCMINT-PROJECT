import re
import json
import requests
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from .config import load_settings
from .media import download_media
from .url_security import MAX_REDIRECTS, normalize_and_validate_url, validated_redirect_url

logger = logging.getLogger(__name__)

# Create a session with retries
session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update({'User-Agent': 'SOCMINT-Profile-Enricher/1.0'})

URL_RE = re.compile(r'https?://[\w\-\.\$\%\&\?\=\/#\+\:]+' )
IMAGE_EXT_RE = re.compile(r'https?://[^\s\"]+\.(?:jpg|jpeg|png|gif|webp)', re.IGNORECASE)


def load_json_if_possible(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith('{') or cleaned.startswith('['):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    return None


def extract_urls(text):
    if not text:
        return []
    return list(set(URL_RE.findall(text)))


def extract_media_urls(text):
    if not text:
        return []
    return list(set(IMAGE_EXT_RE.findall(text)))


def scrape_profile_url(url):
    time.sleep(1)  # Rate limit: 1 req/sec
    settings = load_settings(require_secret=False)
    url = normalize_and_validate_url(url, allow_onion=bool(settings.tor_proxy))
    if not url:
        logger.warning("Skipped unsafe profile URL")
        return None

    request_kwargs = {'timeout': 15, 'allow_redirects': False}
    if settings.tor_proxy:
        request_kwargs['proxies'] = {'http': settings.tor_proxy, 'https': settings.tor_proxy}
    try:
        response = None
        for _ in range(MAX_REDIRECTS + 1):
            response = session.get(url, **request_kwargs)
            if not response.is_redirect:
                break
            next_url = validated_redirect_url(url, response.headers.get('Location'), allow_onion=bool(settings.tor_proxy))
            response.close()
            if not next_url:
                logger.warning("Skipped unsafe profile redirect")
                return None
            url = next_url
        if response is not None and response.is_redirect:
            response.close()
            return None
        response.raise_for_status()
        logger.info("Scraped profile URL: %s", url)
    except Exception as e:
        logger.error("Failed to scrape %s: %s", url, e)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    result = {
        'url': url,
        'title': None,
        'description': None,
        'site_name': None,
        'image': None,
        'raw_html': None,
    }

    title = soup.find('title')
    if title:
        result['title'] = title.get_text(strip=True)

    def meta(name):
        tag = soup.find('meta', attrs={'name': name})
        if tag and tag.get('content'):
            return tag.get('content').strip()
        tag = soup.find('meta', attrs={'property': name})
        if tag and tag.get('content'):
            return tag.get('content').strip()
        return None

    result['description'] = meta('description') or meta('og:description')
    result['site_name'] = meta('og:site_name')
    result['image'] = meta('og:image') or meta('twitter:image')
    result['raw_html'] = response.text[:10000]
    return result


def parse_tool_output(tool_name, raw_output):
    parsed = {
        'tool': tool_name,
        'raw': raw_output,
        'urls': [],
        'media_urls': [],
        'json': None,
    }
    if isinstance(raw_output, str):
        parsed['urls'] = extract_urls(raw_output)
        parsed['media_urls'] = extract_media_urls(raw_output)
        parsed_json = load_json_if_possible(raw_output)
        if parsed_json is not None:
            parsed['json'] = parsed_json
            if isinstance(parsed_json, dict):
                json_text = json.dumps(parsed_json)
                parsed['urls'] = list(set(parsed['urls'] + extract_urls(json_text)))
                parsed['media_urls'] = list(set(parsed['media_urls'] + extract_media_urls(json_text)))
    else:
        try:
            parsed['json'] = raw_output
            parsed['urls'] = extract_urls(json.dumps(raw_output))
        except Exception:
            pass
    return parsed


def enrich_dossier(dossier):
    dossier.setdefault('profiles', [])
    dossier.setdefault('media', [])
    seen_urls = set()
    max_urls = 20  # Limit per dossier

    for tool_name, raw_output in dossier.get('data', {}).items():
        if len(seen_urls) >= max_urls:
            break
        parsed = parse_tool_output(tool_name, raw_output)
        for url in parsed['urls']:
            if url in seen_urls or len(seen_urls) >= max_urls:
                continue
            seen_urls.add(url)
            profile = scrape_profile_url(url)
            if profile:
                dossier['profiles'].append(profile)
                if profile.get('image'):
                    media_meta = download_media(dossier['target'], profile['image'])
                    if media_meta:
                        dossier['media'].append(media_meta)

        for media_url in parsed['media_urls']:
            if media_url in seen_urls or len(seen_urls) >= max_urls:
                continue
            seen_urls.add(media_url)
            media_meta = download_media(dossier['target'], media_url)
            if media_meta:
                dossier['media'].append(media_meta)

    return dossier
