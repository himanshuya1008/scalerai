import re
import os
from typing import List, Tuple, Dict

# Load optional gazetteer
_GAZETTEER = set()
gz_path = os.path.join(os.path.dirname(__file__), "..", "data", "gazetteer_companies.txt")
if os.path.exists(gz_path):
    try:
        with open(gz_path, "r", encoding="utf-8") as gf:
            for line in gf:
                l = line.strip()
                if l:
                    _GAZETTEER.add(l.lower())
    except Exception:
        _GAZETTEER = set()

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None


def luhn_check(card_number: str) -> bool:
    """Return True if card_number passes Luhn check."""
    try:
        digits = [int(d) for d in card_number]
    except Exception:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def check_context_keywords(text: str, match_start: int, keywords: List[str], window: int = 45) -> bool:
    """Check if any of the keywords are present in the text preceding match_start within window."""
    start_idx = max(0, match_start - window)
    context = text[start_idx:match_start].lower()
    return any(k in context for k in keywords)


def regex_detectors(text: str) -> List[Dict]:
    """Return list of detections as dicts with keys: type, start, end, text."""
    detections = []

    # 1. Email
    for m in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
        detections.append({
            "type": "EMAIL",
            "start": m.start(),
            "end": m.end(),
            "text": m.group(0)
        })

    # 2. Phone (with context validation to reduce false positives)
    phone_keywords = ["phone", "mobile", "tel", "contact", "call", "fax", "number", "cell", "ext"]
    for m in re.finditer(r"(?:\+\d{1,3}[\s-]?)?\b(?:\d[\s-]?){9,15}\d\b", text):
        val = m.group(0)
        digits_only = re.sub(r"[^0-9]", "", val)
        if 10 <= len(digits_only) <= 15:
            # High confidence if starts with + or has context keywords
            if val.startswith("+") or check_context_keywords(text, m.start(), phone_keywords, window=35):
                detections.append({
                    "type": "PHONE",
                    "start": m.start(),
                    "end": m.end(),
                    "text": val
                })

    # 3. IP address (IPv4 validation and version exclusion)
    for m in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        val = m.group(0)
        parts = val.split('.')
        if all(0 <= int(p) <= 255 for p in parts):
            # Exclude version numbers (e.g. "version 1.2.3.4")
            prefix_context = text[max(0, m.start() - 15):m.start()].lower()
            if not any(v in prefix_context for v in ["version", "v.", "build"]):
                detections.append({
                    "type": "IP_ADDRESS",
                    "start": m.start(),
                    "end": m.end(),
                    "text": val
                })

    # 4. SSN (US style with dashes and context validation)
    ssn_keywords = ["ssn", "social security", "tax", "tin", "id", "employee", "member", "security"]
    for m in re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", text):
        if check_context_keywords(text, m.start(), ssn_keywords, window=40):
            detections.append({
                "type": "SSN",
                "start": m.start(),
                "end": m.end(),
                "text": m.group(0)
            })

    # 5. Credit card (Luhn check + context validation)
    cc_keywords = ["card", "credit", "payment", "visa", "mastercard", "cc", "card number", "pan", "expiration", "cvv"]
    for m in re.finditer(r"\b(?:\d[ -]*?){13,16}\b", text):
        val = m.group(0)
        digits_only = re.sub(r"[^0-9]", "", val)
        if 13 <= len(digits_only) <= 16 and luhn_check(digits_only):
            if check_context_keywords(text, m.start(), cc_keywords, window=45):
                detections.append({
                    "type": "CREDIT_CARD",
                    "start": m.start(),
                    "end": m.end(),
                    "text": val
                })

    # 6. Date of Birth (restricted to DOB context)
    month_names = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
    date_pattern = rf"\b\d{{1,2}}[\/\-]\d{{1,2}}[\/\-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b{month_names}[\s\-]\d{{1,2}}[,\s]+\d{{4}}\b|\b\d{{1,2}}[\s\-]{month_names}[,\s]+\d{{4}}\b"
    dob_keywords = ["date of birth", "dob", "birth date", "born", "d.o.b."]
    for m in re.finditer(date_pattern, text, flags=re.IGNORECASE):
        if check_context_keywords(text, m.start(), dob_keywords, window=45):
            detections.append({
                "type": "DOB",
                "start": m.start(),
                "end": m.end(),
                "text": m.group(0)
            })

    # 7. Zip/Pincodes as potential ADDRESS components
    for m in re.finditer(r"\b\d{6}\b|\b\d{5}(?:-\d{4})?\b", text):
        detections.append({
            "type": "ADDRESS",
            "start": m.start(),
            "end": m.end(),
            "text": m.group(0)
        })

    # 8. Address Label rule: Address: <value>
    for m in re.finditer(r"\b(?:Address|Addr):\s*([^:\n\r]+?)(?=\s*[A-Z][a-z]+:|\n|\r|$)", text, flags=re.IGNORECASE):
        detections.append({
            "type": "ADDRESS",
            "start": m.start(1),
            "end": m.end(1),
            "text": m.group(1).strip()
        })

    # 9. Company Label rule: Company: <value>
    for m in re.finditer(r"\b(?:Company|Organization|Employer):\s*([A-Z][a-zA-Z0-9.&]*(?:\s+[A-Z][a-zA-Z0-9.&]*)*)", text, flags=re.IGNORECASE):
        detections.append({
            "type": "COMPANY",
            "start": m.start(1),
            "end": m.end(1),
            "text": m.group(1).strip()
        })

    # 10. Company Regex Rule (Capitalized prefix + company suffix)
    company_suffix_pattern = r"\b(?:[A-Z][a-zA-Z0-9.&]*\s+)+(?:Private\s+Limited|Pvt\s+Ltd|Limited|Ltd|Corporation|Corp|Inc|LLP|Technologies|Industries|Bank|Financial|Services)\b"
    for m in re.finditer(company_suffix_pattern, text):
        detections.append({
            "type": "COMPANY",
            "start": m.start(),
            "end": m.end(),
            "text": m.group(0)
        })

    return detections


def ner_detectors(text: str) -> List[Dict]:
    detections = []
    if _nlp is None:
        return detections
    doc = _nlp(text)
    
    # Exclude common field labels from NER candidates
    label_keywords = {
        "email", "phone", "address", "ssn", "credit card", "ip address", 
        "company", "date of birth", "dob", "contact person", "full name", 
        "customer name", "customer full name", "contact email", "organization", 
        "employer", "prospectus", "note", "order number", "order"
    }

    for ent in doc.ents:
        cleaned_ent_text = ent.text.lower().strip().replace(":", "")
        if cleaned_ent_text in label_keywords or any(cleaned_ent_text == lk for lk in label_keywords):
            continue

        # Filter PERSONs
        if ent.label_ == "PERSON":
            has_name_prefix = check_context_keywords(text, ent.start_char, ["name", "person", "mr.", "ms.", "mrs.", "dr.", "contact"], window=20)
            if len(ent.text.split()) >= 2 or has_name_prefix:
                if not any(w in ent.text.lower() for w in ["order", "number", "invoice", "date", "apply", "test", "file", "information"]):
                    detections.append({
                        "type": "PERSON",
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "text": ent.text
                    })
            continue

        # Filter ORG -> COMPANY
        if ent.label_ == "ORG":
            org_text = ent.text
            suffixes = ["ltd", "pvt", "limited", "inc", "llp", "labs", "technologies", "company", "corp", "corporation", "solutions", "industries", "bank", "services"]
            # Strict ORG check: must contain suffix or be in gazetteer to prevent false positives on general text
            if any(suf in org_text.lower() for suf in suffixes) or org_text.lower() in _GAZETTEER:
                detections.append({
                    "type": "COMPANY",
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "text": ent.text
                })
            continue

        # GPE/LOC/FAC -> ADDRESS
        if ent.label_ in ("GPE", "LOC", "FAC"):
            addr_keywords = ["plot", "sector", "street", "road", "apt", "apartment", "bangalore", "pune", "mumbai", "address", "lane", "block", "city", "residency", "flat"]
            if any(k in ent.text.lower() for k in addr_keywords) or len(ent.text.split()) >= 2:
                detections.append({
                    "type": "ADDRESS",
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "text": ent.text
                })
            continue

    return detections


def merge_addresses(detections: List[Dict], text: str) -> List[Dict]:
    """Merge adjacent or overlapping ADDRESS detections in the text."""
    address_dets = [d for d in detections if d["type"] == "ADDRESS"]
    other_dets = [d for d in detections if d["type"] != "ADDRESS"]

    if not address_dets:
        return detections

    address_dets.sort(key=lambda x: x["start"])

    merged_address_dets = []
    current = address_dets[0]

    for next_det in address_dets[1:]:
        gap_start = current["end"]
        gap_end = next_det["start"]
        
        if gap_end <= gap_start:
            current["end"] = max(current["end"], next_det["end"])
            current["text"] = text[current["start"]:current["end"]]
        elif gap_end - gap_start <= 15:
            gap_text = text[gap_start:gap_end].strip()
            if re.match(r"^[,\s\-]*$|^[,\s\-]*(?:in|at|near|of)[,\s\-]*$", gap_text, flags=re.IGNORECASE):
                current["end"] = next_det["end"]
                current["text"] = text[current["start"]:current["end"]]
            else:
                merged_address_dets.append(current)
                current = next_det
        else:
            merged_address_dets.append(current)
            current = next_det

    merged_address_dets.append(current)

    for d in merged_address_dets:
        d["text"] = d["text"].strip(", ")
        stripped_text = d["text"]
        start_offset = text[d["start"]:d["end"]].find(stripped_text)
        if start_offset != -1:
            d["start"] = d["start"] + start_offset
            d["end"] = d["start"] + len(stripped_text)

    return other_dets + merged_address_dets


def resolve_overlaps(detections: List[Dict]) -> List[Dict]:
    """Sort and resolve overlapping spans by preferring longer spans."""
    sorted_dets = sorted(detections, key=lambda x: (x["start"], -x["end"]))
    resolved = []
    for det in sorted_dets:
        overlap = False
        for accepted in resolved:
            if max(det["start"], accepted["start"]) < min(det["end"], accepted["end"]):
                overlap = True
                break
        if not overlap:
            resolved.append(det)
    resolved.sort(key=lambda x: x["start"])
    return resolved


def detect_all(text: str) -> List[Dict]:
    """Return merged and overlap-resolved detections."""
    raw = []
    raw.extend(regex_detectors(text))
    raw.extend(ner_detectors(text))
    
    # Merge nearby address components
    merged = merge_addresses(raw, text)
    
    # Resolve overlapping spans (prefer larger spans)
    final_detections = resolve_overlaps(merged)
    
    return final_detections
