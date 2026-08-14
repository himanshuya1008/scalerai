import re
from typing import List, Dict
from .base import BaseDetector, is_context_keyword_present

class DOBDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        m_names = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
        dob_pattern = rf"\b\d{{1,2}}[\/\-]\d{{1,2}}[\/\-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b{m_names}[\s\-]\d{{1,2}}[,\s]+\d{{4}}\b|\b\d{{1,2}}[\s\-]{m_names}[,\s]+\d{{4}}\b"
        dob_tokens = ["date of birth", "dob", "birth date", "born", "d.o.b."]
        for match in re.finditer(dob_pattern, text, flags=re.IGNORECASE):
            if is_context_keyword_present(text, match.start(), dob_tokens, scan_window=45):
                detections.append({
                    "type": "DOB",
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(0)
                })
        return detections
