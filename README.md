# PII Redaction Tool

PII Redaction Tool — professionalized

Overview

This project implements a hybrid PII detection and anonymization pipeline for DOCX documents. It combines deterministic regex detectors (email, phone, IP, SSN, credit card, dates) with spaCy NER (names, organizations, locations). Replacements use `faker` and are persisted so repeated occurrences map to the same pseudonym.

What I improved

- Per-container detection (paragraphs / table cells / headers) to avoid run-splitting replacement issues.
- Smarter detectors: Luhn validation for credit cards, stricter phone validation, improved date regex, and NER filters for PERSON/ORG/ADDRESS to reduce false positives.
- Evaluation: fuzzy matching (substring overlap) and per-type metrics with a human-friendly markdown report.

Quick start

1. Create a Python venv and install requirements:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1   # or .venv\Scripts\activate for cmd
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

2. Run the redactor on a file (example):

```powershell
python src/main.py --input "input/Red Herring Prospectus_Redacted.docx" --output "output/redacted.docx" --ground_truth tests/ground_truth.json
```

Outputs

- `output/redacted.docx` — redacted document
- `output/mapping.json` — mapping from original → fake (persists between runs)
- `reports/evaluation_report.md` — formatted evaluation when `--ground_truth` provided

Project layout

```
scalerai/
├─ src/                # source modules (detectors, extractor, writer, anonymizer, evaluator)
├─ input/              # input DOCX files (put prospectus here)
├─ output/             # redacted.docx and mapping.json
├─ reports/            # evaluation report
├─ tests/              # ground-truth examples for evaluation
├─ requirements.txt
└─ README.md
```

Next improvements you can request

- Expand ground-truth and run evaluation on a real prospectus for reliable metrics.
- Add more conservative company/address heuristics or a small gazetteer of cities/terms to reduce false positives.
- Integrate Microsoft Presidio for production-grade PII detection.
- Add unit tests and CI integration.

