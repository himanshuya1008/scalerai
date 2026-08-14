import re
import os
from typing import List, Tuple, Dict

# Load optional custom gazetteer for companies
COMPANY_GAZETTEER = set()
gazetteer_file_path = os.path.join(os.path.dirname(__file__), "..", "data", "gazetteer_companies.txt")
if os.path.exists(gazetteer_file_path):
    try:
        with open(gazetteer_file_path, "r", encoding="utf-8") as stream:
            for val in stream:
                normalized_line = val.strip().lower()
                if normalized_line:
                    COMPANY_GAZETTEER.add(normalized_line)
    except Exception:
        COMPANY_GAZETTEER = set()

# Initialize spaCy package
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None


def luhn_check(card_number: str) -> bool:
    """Verifies credit card numbers using Luhn's algorithm checksum validation."""
    try:
        digits_array = [int(char) for char in card_number if char.isdigit()]
    except Exception:
        return False
    if not digits_array:
        return False
    # Alternative arithmetic sum representation to verify Luhn condition
    checksum_sum = sum(digits_array[-1::-2]) + sum(sum(divmod(d * 2, 10)) for d in digits_array[-2::-2])
    return checksum_sum % 10 == 0


def is_context_keyword_present(text_content: str, index_pos: int, keyword_list: List[str], scan_window: int = 45) -> bool:
    """Searches backward from a given position within a specified window for control words."""
    left_boundary = max(0, index_pos - scan_window)
    preceding_context = text_content[left_boundary:index_pos].lower()
    return any(word in preceding_context for word in keyword_list)


def regex_detectors(text: str) -> List[Dict]:
    """Applies regex patterns to identify deterministic PII types in text."""
    detections_list = []

    # 1. Emails
    for match in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
        detections_list.append({
            "type": "EMAIL",
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0)
        })

    # 2. Phones
    phone_tokens = ["phone", "mobile", "tel", "contact", "call", "fax", "number", "cell", "ext"]
    for match in re.finditer(r"(?:\+\d{1,3}[\s-]?)?\b(?:\d[\s-]?){9,15}\d\b", text):
        val = match.group(0)
        only_nums = re.sub(r"\D", "", val)
        if 10 <= len(only_nums) <= 15:
            # Valid if context keyword is adjacent or starts with +
            if val.startswith("+") or is_context_keyword_present(text, match.start(), phone_tokens, scan_window=35):
                detections_list.append({
                    "type": "PHONE",
                    "start": match.start(),
                    "end": match.end(),
                    "text": val
                })

    # 3. IP Addresses
    for match in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        val = match.group(0)
        segments = val.split(".")
        if all(0 <= int(part) <= 255 for part in segments):
            left_context = text[max(0, match.start() - 15):match.start()].lower()
            # Prevent catching software versions
            if not any(indicator in left_context for indicator in ["version", "v.", "build"]):
                detections_list.append({
                    "type": "IP_ADDRESS",
                    "start": match.start(),
                    "end": match.end(),
                    "text": val
                })

    # 4. SSN
    ssn_tokens = ["ssn", "social security", "tax", "tin", "id", "employee", "member", "security"]
    for match in re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", text):
        if is_context_keyword_present(text, match.start(), ssn_tokens, scan_window=40):
            detections_list.append({
                "type": "SSN",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0)
            })

    # 5. Credit Cards
    cc_tokens = ["card", "credit", "payment", "visa", "mastercard", "cc", "card number", "pan", "expiration", "cvv"]
    for match in re.finditer(r"\b(?:\d[ -]*?){13,16}\b", text):
        val = match.group(0)
        only_digits = re.sub(r"\D", "", val)
        if 13 <= len(only_digits) <= 16 and luhn_check(only_digits):
            if is_context_keyword_present(text, match.start(), cc_tokens, scan_window=45):
                detections_list.append({
                    "type": "CREDIT_CARD",
                    "start": match.start(),
                    "end": match.end(),
                    "text": val
                })

    # 6. Dates of Birth
    m_names = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
    dob_pattern = rf"\b\d{{1,2}}[\/\-]\d{{1,2}}[\/\-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b{m_names}[\s\-]\d{{1,2}}[,\s]+\d{{4}}\b|\b\d{{1,2}}[\s\-]{m_names}[,\s]+\d{{4}}\b"
    dob_tokens = ["date of birth", "dob", "birth date", "born", "d.o.b."]
    for match in re.finditer(dob_pattern, text, flags=re.IGNORECASE):
        if is_context_keyword_present(text, match.start(), dob_tokens, scan_window=45):
            detections_list.append({
                "type": "DOB",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0)
            })

    # 7. Zip/Pincodes
    for match in re.finditer(r"\b\d{6}\b|\b\d{5}(?:-\d{4})?\b", text):
        detections_list.append({
            "type": "ADDRESS",
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0)
        })

    # 8. Address Label Syntax
    for match in re.finditer(r"\b(?:Address|Addr):\s*([^:\n\r]+?)(?=\s*[A-Z][a-z]+:|\n|\r|$)", text, flags=re.IGNORECASE):
        detections_list.append({
            "type": "ADDRESS",
            "start": match.start(1),
            "end": match.end(1),
            "text": match.group(1).strip()
        })

    # 9. Company Label Syntax
    for match in re.finditer(r"\b(?:Company|Organization|Employer):\s*([A-Z][a-zA-Z0-9.&]*(?:\s+[A-Z][a-zA-Z0-9.&]*)*)", text, flags=re.IGNORECASE):
        detections_list.append({
            "type": "COMPANY",
            "start": match.start(1),
            "end": match.end(1),
            "text": match.group(1).strip()
        })

    # 10. Company Suffix Pattern
    company_suffix_pattern = r"\b(?:[A-Z][a-zA-Z0-9.&]*\s+)+(?:Private\s+Limited|Pvt\s+Ltd|Limited|Ltd|Corporation|Corp|Inc|LLP|Technologies|Industries|Bank|Financial|Services)\b"
    for match in re.finditer(company_suffix_pattern, text):
        detections_list.append({
            "type": "COMPANY",
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0)
        })

    return detections_list


def ner_detectors_from_doc(doc, text: str) -> List[Dict]:
    """Helper to extract candidates from a precompiled spaCy doc object."""
    candidates_list = []
    
    stop_labels = {
        "email", "phone", "address", "ssn", "credit card", "ip address", 
        "company", "date of birth", "dob", "contact person", "full name", 
        "customer name", "customer full name", "contact email", "organization", 
        "employer", "prospectus", "note", "order number", "order"
    }

    for entity in doc.ents:
        norm_ent = entity.text.lower().strip().replace(":", "")
        if norm_ent in stop_labels or any(norm_ent == sl for sl in stop_labels):
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


def ner_detectors(text: str) -> List[Dict]:
    """Runs spaCy NER model to identify persons, companies, and locations in text."""
    if _nlp is None:
        return []
    doc_obj = _nlp(text)
    return ner_detectors_from_doc(doc_obj, text)


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


def detect_all(text: str) -> List[Dict]:
    """Combines regex and NER detectors, resolves conflicts, and yields merged spans."""
    raw_spans = []
    raw_spans.extend(regex_detectors(text))
    raw_spans.extend(ner_detectors(text))
    
    # Consolidate nearby address pieces
    merged_spans = merge_addresses(raw_spans, text)
    
    # Filter out overlapping sub-spans
    return resolve_overlaps(merged_spans)
