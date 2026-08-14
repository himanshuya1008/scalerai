import re
from typing import List, Dict
from .base import BaseDetector

class IPDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        for match in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
            val = match.group(0)
            segments = val.split(".")
            if all(0 <= int(part) <= 255 for part in segments):
                left_context = text[max(0, match.start() - 15):match.start()].lower()
                # Prevent catching software versions
                if not any(indicator in left_context for indicator in ["version", "v.", "build"]):
                    detections.append({
                        "type": "IP_ADDRESS",
                        "start": match.start(),
                        "end": match.end(),
                        "text": val
                    })
        return detections
