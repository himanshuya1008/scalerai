import re
from typing import List, Dict
from .base import BaseDetector, is_context_keyword_present

class SSNDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        ssn_tokens = ["ssn", "social security", "tax", "tin", "id", "employee", "member", "security"]
        for match in re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", text):
            if is_context_keyword_present(text, match.start(), ssn_tokens, scan_window=40):
                detections.append({
                    "type": "SSN",
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(0)
                })
        return detections
