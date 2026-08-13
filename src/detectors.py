import re
from typing import List, Tuple, Dict
import os

# load optional gazetteer
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


def regex_detectors(text: str) -> List[Tuple[str, int, int, str]]:
    """Return list of (type, start, end, text) from regex detectors."""
    detections = []
    # Email
    for m in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
        detections.append(("EMAIL", m.start(), m.end(), m.group(0)))

    # Phone (improved: international with spaces/dashes, require 10-15 digits)
    for m in re.finditer(r"\b(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){9,15}\d\b", text):
        candidate = re.sub(r"[^0-9]", "", m.group(0))
        if 10 <= len(candidate) <= 15:
            detections.append(("PHONE", m.start(), m.end(), m.group(0)))

    # IP address
    for m in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        detections.append(("IP", m.start(), m.end(), m.group(0)))

    # SSN (US style)
    for m in re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", text):
        detections.append(("SSN", m.start(), m.end(), m.group(0)))

    # Credit card (groups of 13-16 digits with spaces/dashes) + Luhn validation
    for m in re.finditer(r"\b(?:\d[ -]*?){13,16}\b", text):
        candidate = re.sub(r"[^0-9]", "", m.group(0))
        if 13 <= len(candidate) <= 16 and luhn_check(candidate):
            detections.append(("CREDIT_CARD", m.start(), m.end(), m.group(0)))

    # Dates: dd/mm/yyyy, yyyy-mm-dd, or 'Aug 10 2026' / '10 Aug 2026'
    month_names = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
    date_pattern = rf"\b\d{{1,2}}[\/\-]\d{{1,2}}[\/\-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b{month_names}[\s\-]\d{{1,2}}[,\s]+\d{{4}}\b|\b\d{{1,2}}[\s\-]{month_names}[,\s]+\d{{4}}\b"
    for m in re.finditer(date_pattern, text, flags=re.IGNORECASE):
        detections.append(("DATE", m.start(), m.end(), m.group(0)))

    return detections


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


def ner_detectors(text: str) -> List[Tuple[str, int, int, str]]:
    detections = []
    if _nlp is None:
        return detections
    doc = _nlp(text)
    for ent in doc.ents:
        # Filter PERSONs: prefer multi-token names (first + last)
        if ent.label_ == "PERSON":
            if len(ent.text.split()) >= 2:
                detections.append(("NAME", ent.start_char, ent.end_char, ent.text))
            continue

        # Filter ORG: require common company suffix or multi-word ORG
        if ent.label_ == "ORG":
            org_text = ent.text
            suffixes = ["Ltd", "Pvt", "Limited", "Inc", "LLP", "Labs", "Technologies", "Company", "Corp", "Corporation", "Solutions"]
            # prefer orgs with suffixes or in gazetteer
            if any(suf.lower() in org_text.lower() for suf in suffixes) or len(org_text.split()) >= 2 or org_text.lower() in _GAZETTEER:
                detections.append(("COMPANY", ent.start_char, ent.end_char, ent.text))
            continue

        # GPE/LOC as ADDRESS only if address-like keywords exist
        if ent.label_ in ("GPE", "LOC"):
            addr_keywords = ["Plot", "Sector", "Street", "Road", "Apt", "Apartment", "Bangalore", "Pune", "Mumbai", "Address", "Lane", "Block", "City"]
            if any(k.lower() in ent.text.lower() for k in addr_keywords):
                detections.append(("ADDRESS", ent.start_char, ent.end_char, ent.text))
            else:
                # also allow single-city GPEs as ADDRESS if capitalized short tokens
                if len(ent.text.split()) == 1:
                    detections.append(("ADDRESS", ent.start_char, ent.end_char, ent.text))
            continue

        if ent.label_ == "DATE":
            detections.append(("DATE", ent.start_char, ent.end_char, ent.text))
    return detections


def detect_all(text: str) -> List[Dict]:
    """Return merged detections as dicts with keys: type,start,end,text."""
    raw = []
    raw.extend(regex_detectors(text))
    raw.extend(ner_detectors(text))
    # Merge/normalize into dicts
    results = []
    for t, s, e, txt in raw:
        results.append({"type": t, "start": s, "end": e, "text": txt})
    # Sort by start
    results.sort(key=lambda x: x["start"])
    return results
