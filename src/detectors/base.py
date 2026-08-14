import re
from typing import List, Dict

# spaCy loading
_nlp = None
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"WARNING: spaCy or 'en_core_web_sm' model could not be loaded. PERSON names detection will be disabled. Error: {e}")
    _nlp = None


def luhn_check(card_number: str) -> bool:
    """Verifies credit card numbers using Luhn's algorithm checksum validation."""
    try:
        digits_array = [int(char) for char in card_number if char.isdigit()]
    except Exception:
        return False
    if not digits_array:
        return False
    checksum_sum = sum(digits_array[-1::-2]) + sum(sum(divmod(d * 2, 10)) for d in digits_array[-2::-2])
    return checksum_sum % 10 == 0


def is_context_keyword_present(text_content: str, index_pos: int, keyword_list: List[str], scan_window: int = 45) -> bool:
    """Searches backward from a given position within a specified window for control words."""
    left_boundary = max(0, index_pos - scan_window)
    preceding_context = text_content[left_boundary:index_pos].lower()
    return any(word in preceding_context for word in keyword_list)


class BaseDetector:
    """Abstract base class for all PII detectors."""
    def detect(self, text: str, **kwargs) -> List[Dict]:
        raise NotImplementedError
