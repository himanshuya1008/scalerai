import re
from typing import List, Dict
from .base import BaseDetector, _nlp, is_context_keyword_present

class NameDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []

        # 1. Name Salutation Pattern (e.g., Mr. Rashi Patil, Dr. John Doe)
        for match in re.finditer(r"\b(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b", text):
            detections.append({
                "type": "PERSON",
                "start": match.start(1),
                "end": match.end(1),
                "text": match.group(1).strip()
            })

        # 2. Name Prefix Pattern (e.g., Name: Rashi Patil, Contact Person: Rohan Mehta)
        for match in re.finditer(r"\b(?:Name|Director|Contact Person|Representative):\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b", text, flags=re.IGNORECASE):
            detections.append({
                "type": "PERSON",
                "start": match.start(1),
                "end": match.end(1),
                "text": match.group(1).strip()
            })

        # 3. spaCy PERSON NER
        spacy_doc = kwargs.get("spacy_doc")
        if spacy_doc is None and _nlp is not None:
            spacy_doc = _nlp(text)

        if spacy_doc is not None:
            stop_labels = {
                "email", "phone", "address", "ssn", "credit card", "ip address", 
                "company", "date of birth", "dob", "contact person", "full name", 
                "customer name", "customer full name", "contact email", "organization", 
                "employer", "prospectus", "note", "order number", "order"
            }
            for entity in spacy_doc.ents:
                norm_ent = entity.text.lower().strip().replace(":", "")
                if norm_ent in stop_labels:
                    continue
                if entity.label_ == "PERSON":
                    is_valid_prefix = is_context_keyword_present(text, entity.start_char, ["name", "person", "mr.", "ms.", "mrs.", "dr.", "contact"], scan_window=20)
                    if len(entity.text.split()) >= 2 or is_valid_prefix:
                        if not any(w in entity.text.lower() for w in ["order", "number", "invoice", "date", "apply", "test", "file", "information"]):
                            detections.append({
                                "type": "PERSON",
                                "start": entity.start_char,
                                "end": entity.end_char,
                                "text": entity.text
                            })
        return detections
