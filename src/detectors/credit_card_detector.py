import re
from typing import List, Dict
from .base import BaseDetector, luhn_check, is_context_keyword_present

class CreditCardDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        cc_tokens = ["card", "credit", "payment", "visa", "mastercard", "cc", "card number", "pan", "expiration", "cvv"]
        for match in re.finditer(r"\b(?:\d[ -]*?){13,16}\b", text):
            val = match.group(0)
            only_digits = re.sub(r"\D", "", val)
            if 13 <= len(only_digits) <= 16 and luhn_check(only_digits):
                if is_context_keyword_present(text, match.start(), cc_tokens, scan_window=45):
                    detections.append({
                        "type": "CREDIT_CARD",
                        "start": match.start(),
                        "end": match.end(),
                        "text": val
                    })
        return detections
