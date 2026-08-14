import re
import os
from typing import List, Dict
from .base import BaseDetector, _nlp

# Load optional custom gazetteer for companies
COMPANY_GAZETTEER = set()
gazetteer_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "gazetteer_companies.txt")
if os.path.exists(gazetteer_file_path):
    try:
        with open(gazetteer_file_path, "r", encoding="utf-8") as stream:
            for val in stream:
                normalized_line = val.strip().lower()
                if normalized_line:
                    COMPANY_GAZETTEER.add(normalized_line)
    except Exception:
        COMPANY_GAZETTEER = set()


class CompanyDetector(BaseDetector):
    def detect(self, text: str, **kwargs) -> List[Dict]:
        detections = []

        # 1. Company Label Syntax
        for match in re.finditer(r"\b(?:Company|Organization|Employer):\s*([A-Z][a-zA-Z0-9.&]*(?:\s+[A-Z][a-zA-Z0-9.&]*)*)", text, flags=re.IGNORECASE):
            detections.append({
                "type": "COMPANY",
                "start": match.start(1),
                "end": match.end(1),
                "text": match.group(1).strip()
            })

        # 2. Company Suffix Pattern
        company_suffix_pattern = r"\b(?:[A-Z][a-zA-Z0-9.&]*\s+)+(?:Private\s+Limited|Pvt\s+Ltd|Limited|Ltd|Corporation|Corp|Inc|LLP|Technologies|Industries|Bank|Financial|Services)\b"
        for match in re.finditer(company_suffix_pattern, text):
            detections.append({
                "type": "COMPANY",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0)
            })

        # 3. spaCy ORG NER
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
                if entity.label_ == "ORG":
                    org_val = entity.text
                    corp_suffixes = ["ltd", "pvt", "limited", "inc", "llp", "labs", "technologies", "company", "corp", "corporation", "solutions", "industries", "bank", "services"]
                    if any(suf in org_val.lower() for suf in corp_suffixes) or org_val.lower() in COMPANY_GAZETTEER:
                        detections.append({
                            "type": "COMPANY",
                            "start": entity.start_char,
                            "end": entity.end_char,
                            "text": entity.text
                        })
        return detections
