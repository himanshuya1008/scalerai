import re
from typing import List, Dict
from .base import BaseDetector

class EmailDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        for match in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
            detections.append({
                "type": "EMAIL",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0)
            })
        return detections
