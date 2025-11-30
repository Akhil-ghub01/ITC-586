from typing import Literal

SafetyFlag = Literal["normal", "unsafe", "out_of_scope"]


UNSAFE_KEYWORDS = [
    "suicide",
    "kill myself",
    "kill him",
    "kill her",
    "murder",
    "self harm",
    "self-harm",
    "bomb",
    "explosive",
    "terrorist",
]

OUT_OF_SCOPE_KEYWORDS = [
    "diagnose",
    "medical advice",
    "medicine for",
    "prescription",
    "crypto trading",
    "stock tip",
    "investment advice",
    "tax advice",
    "legal advice",
]


def classify_safety(text: str) -> SafetyFlag:
    """
    Very basic classifier:
      - returns "unsafe"       if clear self-harm / violence keywords
      - returns "out_of_scope" for medical/financial/legal-style keywords
      - else "normal"
    """
    s = (text or "").lower()

    for kw in UNSAFE_KEYWORDS:
        if kw in s:
            return "unsafe"

    for kw in OUT_OF_SCOPE_KEYWORDS:
        if kw in s:
            return "out_of_scope"

    return "normal"
