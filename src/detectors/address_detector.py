import re
from typing import List, Dict
from .base import BaseDetector, _nlp

class AddressDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []
        
        # 1. Zip / Pincodes
        for match in re.finditer(r"\b\d{6}\b|\b\d{5}(?:-\d{4})?\b", text):
            detections.append({
                "type": "ADDRESS",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0)
            })

        # 2. Address Label Syntax
        for match in re.finditer(r"\b(?:Address|Addr):\s*([^:\n\r]+?)(?=\s*[A-Z][a-z]+:|\n|\r|$)", text, flags=re.IGNORECASE):
            detections.append({
                "type": "ADDRESS",
                "start": match.start(1),
                "end": match.end(1),
                "text": match.group(1).strip()
            })

        # 3. spaCy GPE/LOC/FAC NER
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
                if entity.label_ in ("GPE", "LOC", "FAC"):
                    loc_tokens = ["plot", "sector", "street", "road", "apt", "apartment", "bangalore", "pune", "mumbai", "address", "lane", "block", "city", "residency", "flat"]
                    if any(token in entity.text.lower() for token in loc_tokens) or len(entity.text.split()) >= 2:
                        detections.append({
                            "type": "ADDRESS",
                            "start": entity.start_char,
                            "end": entity.end_char,
                            "text": entity.text
                        })
        return detections
