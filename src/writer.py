from docx import Document
from typing import List, Dict


def replace_in_run_obj(container, original: str, replacement: str):
    """Replace occurrences of original with replacement in runs of a paragraph or cell."""
    if hasattr(container, "runs"):
        for run in container.runs:
            if original in run.text:
                run.text = run.text.replace(original, replacement)
    else:
        # fallback: set text if possible
        try:
            container.text = container.text.replace(original, replacement)
        except Exception:
            pass


def apply_replacements(doc: Document, replacements: List[Dict]):
    """Apply replacements across entire document. replacements: list of dicts with keys original, replacement"""
    for container, _text in iter_all_text_containers(doc):
        for rep in replacements:
            replace_in_run_obj(container, rep["original"], rep["replacement"])


def apply_replacements_to_container(container, replacements: List[Dict]):
    """Apply replacements only to a single paragraph/cell container."""
    for rep in replacements:
        replace_in_run_obj(container, rep["original"], rep["replacement"])


def iter_all_text_containers(doc: Document):
    # paragraphs
    for p in doc.paragraphs:
        yield p, p.text
    # headers/footers
    for section in doc.sections:
        header = section.header
        footer = section.footer
        if header is not None:
            for p in header.paragraphs:
                yield p, p.text
        if footer is not None:
            for p in footer.paragraphs:
                yield p, p.text
    # tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                yield cell, cell.text
