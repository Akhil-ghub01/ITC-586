import re
from typing import Tuple

# Very simple regex-based PII detectors
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_RE = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)

CARD_RE = re.compile(
    r"\b(?:\d[ -]*?){13,16}\b"
)


def mask_pii(text: str) -> Tuple[str, bool]:
    """
    Return (masked_text, had_pii).
    We mask:
      - emails   -> [EMAIL]
      - phones   -> [PHONE]
      - card-like numbers -> [CARD]
    """
    if not text:
        return text, False

    had_pii = False

    def _sub_and_flag(pattern: re.Pattern, repl: str, s: str) -> str:
        nonlocal had_pii
        if pattern.search(s):
            had_pii = True
            s = pattern.sub(repl, s)
        return s

    masked = text

    masked = _sub_and_flag(EMAIL_RE, "[EMAIL]", masked)
    masked = _sub_and_flag(PHONE_RE, "[PHONE]", masked)
    masked = _sub_and_flag(CARD_RE, "[CARD]", masked)

    return masked, had_pii
