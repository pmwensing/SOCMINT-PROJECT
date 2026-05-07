import hashlib
import re
from dataclasses import dataclass

try:
    import phonenumbers
except Exception:
    phonenumbers = None


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{2,100}$")
URL_RE = re.compile(r"^https?://[^\s]+$", re.I)


@dataclass(frozen=True)
class NormalizedSeed:
    seed_type: str
    raw_value: str
    normalized_value: str
    pii_hash: str


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_seed(raw_value: str, seed_type: str | None = None) -> NormalizedSeed:
    raw = (raw_value or "").strip()
    if not raw:
        raise ValueError("Seed value is required.")

    detected = seed_type or detect_seed_type(raw)

    if detected == "email":
        normalized = raw.lower()
        if not EMAIL_RE.match(normalized):
            raise ValueError("Invalid email seed.")
    elif detected == "username":
        normalized = raw.strip().lstrip("@")
        if not USERNAME_RE.match(normalized):
            raise ValueError("Invalid username seed.")
    elif detected == "phone":
        normalized = normalize_phone(raw)
    elif detected == "url":
        normalized = raw
        if not URL_RE.match(normalized):
            raise ValueError("Invalid URL seed.")
    else:
        raise ValueError(f"Unsupported seed type: {detected}")

    return NormalizedSeed(
        seed_type=detected,
        raw_value=raw,
        normalized_value=normalized,
        pii_hash=stable_hash(f"{detected}:{normalized}"),
    )


def detect_seed_type(raw_value: str) -> str:
    value = raw_value.strip()
    if EMAIL_RE.match(value.lower()):
        return "email"
    if URL_RE.match(value):
        return "url"
    if looks_like_phone(value):
        return "phone"
    return "username"


def looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return 7 <= len(digits) <= 16


def normalize_phone(value: str) -> str:
    if phonenumbers is None:
        digits = re.sub(r"\D", "", value)
        if not digits:
            raise ValueError("Invalid phone seed.")
        return "+" + digits if value.strip().startswith("+") else digits

    try:
        parsed = phonenumbers.parse(value, None)
    except Exception as exc:
        raise ValueError("Invalid phone seed.") from exc

    if not phonenumbers.is_possible_number(parsed):
        raise ValueError("Invalid phone seed.")

    return phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.E164,
    )
