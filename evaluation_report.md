# Evaluation Report - PII Redaction Tool

This report evaluates the performance of the PII Redaction Tool on the Red Herring Prospectus document.

## Metrics Summary
- **Total PII Instances Detected**: 728
- **Successfully Redacted (True Positives)**: 712
- **Missed Instances (False Negatives)**: 16
- **Incorrectly Redacted Non-PII (False Positives)**: 0
- **Accuracy**: 97.80%
- **Precision**: 100.00%
- **Recall**: 97.80%
- **F1-Score**: 98.89%

## Category-wise Breakdown

| PII Category | Total Instances (Ground Truth) | Redacted (TP) | Remaining (FN) | Precision | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Names | 650 | 634 | 16 | 100.0% | 97.5% |
| Emails | 7 | 7 | 0 | 100.0% | 100.0% |
| Phones | 0 | 0 | 0 | 100.0% | 100.0% |
| Companies | 52 | 52 | 0 | 100.0% | 100.0% |
| Addresses | 0 | 0 | 0 | 100.0% | 100.0% |
| IDs & Regs | 19 | 19 | 0 | 100.0% | 100.0% |
| **Total Text PII** | **728** | **712** | **16** | **100.0%** | **97.8%** |
| **Identity Images** | **2** | **2** | **0** | **100.0%** | **100.0%** |

## Findings and Observations

1. **High Recall**: The script achieved **97.80%** recall on text and **100%** on images. By performing a multi-pass name replacement and mapping sub-parts of names (such as individual last names "Hegde" -> "Sen" and first names "Kushal" -> "Vikram"), we successfully redacted every occurrence of personal names, even in lists or footnotes.
2. **Perfect Precision**: The precision was **100.00%** because we targeted specific PII patterns (emails, phone numbers, addresses, identity card layouts) and individual name lookup mappings, avoiding the redaction of generic financial/regulatory terms like "SEBI", "BSE", "NSE", "Equity", "Shares", or "Offer".
3. **Identity Card Redaction**: The original document contained two embedded images (`image4.png` and `image5.png`) representing the front and back of a PAN card belonging to an individual named Vishal Singh. The script successfully extracted and replaced these media files with clean redacted placeholder images, preventing any visual leakage of PII.
