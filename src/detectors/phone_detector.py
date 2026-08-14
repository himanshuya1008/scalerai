import re
from typing import List, Dict
from .base import BaseDetector, is_context_keyword_present

class PhoneDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        phone_tokens = ["phone", "mobile", "tel", "contact", "call", "fax", "number", "cell", "ext"]
        for match in re.finditer(r"(?:\+\d{1,3}[\s-]?)?\b(?:\d[\s-]?){9,15}\d\b", text):
            val = match.group(0)
            only_nums = re.sub(r"\D", "", val)
            if 10 <= len(only_nums) <= 15:
                # Valid if context keyword is adjacent or starts with +
                if val.startswith("+") or is_context_keyword_present(text, match.start(), phone_tokens, scan_window=35):
                    detections.append({
                        "type": "PHONE",
                        "start": match.start(),
                        "end": match.end(),
                        "text": val
                    })
        return detections
