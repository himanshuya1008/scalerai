import re
from typing import List, Dict

from .base import _nlp, luhn_check, is_context_keyword_present
from .email_detector import EmailDetector
from .phone_detector import PhoneDetector
from .ip_detector import IPDetector
from .ssn_detector import SSNDetector
from .credit_card_detector import CreditCardDetector
from .dob_detector import DOBDetector
from .address_detector import AddressDetector
from .company_detector import CompanyDetector
from .name_detector import NameDetector

_all_detectors = [
    EmailDetector(),
    PhoneDetector(),
    IPDetector(),
    SSNDetector(),
    CreditCardDetector(),
    DOBDetector(),
    AddressDetector(),
    CompanyDetector(),
    NameDetector()
]


def detect_all(text: str) -> List[Dict]:
    """Combines all detectors, resolves conflicts, and yields merged spans."""
    spacy_doc = None
    if _nlp is not None:
        try:
            spacy_doc = _nlp(text)
        except Exception:
            spacy_doc = None

    raw_spans = []
    for d in _all_detectors:
        raw_spans.extend(d.detect(text, spacy_doc=spacy_doc))

    merged_spans = merge_addresses(raw_spans, text)
    return resolve_overlaps(merged_spans)


def regex_detectors(text: str) -> List[Dict]:
    """Fallback list of regex-based detections (excluding NER component)."""
    raw_spans = []
    for d in _all_detectors:
        raw_spans.extend(d.detect(text, skip_ner=True))
    return raw_spans


def ner_detectors_from_doc(doc, text: str) -> List[Dict]:
    """Extract candidate PII from a spaCy Doc object (NER only)."""
    candidates_list = []
    
    stop_labels = {
        "email", "phone", "address", "ssn", "credit card", "ip address", 
        "company", "date of birth", "dob", "contact person", "full name", 
        "customer name", "customer full name", "contact email", "organization", 
        "employer", "prospectus", "note", "order number", "order"
    }

    for entity in doc.ents:
        norm_ent = entity.text.lower().strip().replace(":", "")
        if norm_ent in stop_labels:
            continue

        # Extract Person
        if entity.label_ == "PERSON":
            is_valid_prefix = is_context_keyword_present(text, entity.start_char, ["name", "person", "mr.", "ms.", "mrs.", "dr.", "contact"], scan_window=20)
            if len(entity.text.split()) >= 2 or is_valid_prefix:
                if not any(w in entity.text.lower() for w in ["order", "number", "invoice", "date", "apply", "test", "file", "information"]):
                    candidates_list.append({
                        "type": "PERSON",
                        "start": entity.start_char,
                        "end": entity.end_char,
                        "text": entity.text
                    })
            continue

        # Extract ORG -> COMPANY
        if entity.label_ == "ORG":
            from .company_detector import COMPANY_GAZETTEER
            org_val = entity.text
            corp_suffixes = ["ltd", "pvt", "limited", "inc", "llp", "labs", "technologies", "company", "corp", "corporation", "solutions", "industries", "bank", "services"]
            if any(suf in org_val.lower() for suf in corp_suffixes) or org_val.lower() in COMPANY_GAZETTEER:
                candidates_list.append({
                    "type": "COMPANY",
                    "start": entity.start_char,
                    "end": entity.end_char,
                    "text": entity.text
                })
            continue

        # Extract GPE/LOC/FAC -> ADDRESS
        if entity.label_ in ("GPE", "LOC", "FAC"):
            loc_tokens = ["plot", "sector", "street", "road", "apt", "apartment", "bangalore", "pune", "mumbai", "address", "lane", "block", "city", "residency", "flat"]
            if any(token in entity.text.lower() for token in loc_tokens) or len(entity.text.split()) >= 2:
                candidates_list.append({
                    "type": "ADDRESS",
                    "start": entity.start_char,
                    "end": entity.end_char,
                    "text": entity.text
                })
            continue

    return candidates_list


def merge_addresses(detections: List[Dict], text: str) -> List[Dict]:
    """Groups adjacent or overlapping ADDRESS detections together."""
    address_spans = [item for item in detections if item["type"] == "ADDRESS"]
    other_spans = [item for item in detections if item["type"] != "ADDRESS"]

    if not address_spans:
        return detections

    address_spans.sort(key=lambda item: item["start"])

    consolidated = []
    current_span = address_spans[0]

    for next_span in address_spans[1:]:
        gap_start = current_span["end"]
        gap_end = next_span["start"]
        
        if gap_end <= gap_start:
            current_span["end"] = max(current_span["end"], next_span["end"])
            current_span["text"] = text[current_span["start"]:current_span["end"]]
        elif gap_end - gap_start <= 15:
            gap_phrase = text[gap_start:gap_end].strip()
            if re.match(r"^[,\s\-]*$|^[,\s\-]*(?:in|at|near|of)[,\s\-]*$", gap_phrase, flags=re.IGNORECASE):
                current_span["end"] = next_span["end"]
                current_span["text"] = text[current_span["start"]:current_span["end"]]
            else:
                consolidated.append(current_span)
                current_span = next_span
        else:
            consolidated.append(current_span)
            current_span = next_span

    consolidated.append(current_span)

    # Post-process formatting offsets
    for item in consolidated:
        item["text"] = item["text"].strip(", ")
        clean_text = item["text"]
        offset = text[item["start"]:item["end"]].find(clean_text)
        if offset != -1:
            item["start"] = item["start"] + offset
            item["end"] = item["start"] + len(clean_text)

    return other_spans + consolidated


def resolve_overlaps(detections: List[Dict]) -> List[Dict]:
    """Sorts detections and filters out smaller overlapping spans, preferring larger spans."""
    sorted_items = sorted(detections, key=lambda item: (item["start"], -item["end"]))
    non_overlapping = []
    for item in sorted_items:
        overlap = False
        for accepted in non_overlapping:
            if max(item["start"], accepted["start"]) < min(item["end"], accepted["end"]):
                overlap = True
                break
        if not overlap:
            non_overlapping.append(item)
    non_overlapping.sort(key=lambda item: item["start"])
    return non_overlapping
