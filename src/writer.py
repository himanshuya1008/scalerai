from docx import Document
from typing import List, Dict
import re


def collect_paragraph_runs(para_obj) -> list:
    """
    Collects all Run objects recursively inside a paragraph to handle 
    nested text runs (like inside hyperlinks or smart fields) in order.
    """
    all_runs = []
    
    def traverse_element(node):
        for child in node:
            local_name = child.tag.split("}")[-1]
            if local_name == "r":
                from docx.text.run import Run
                all_runs.append(Run(child, para_obj))
            else:
                traverse_element(child)
                
    traverse_element(para_obj._element)
    return all_runs


def fallback_text_replace(element, search_str: str, replace_str: str):
    """Fallback utility to replace text in runs or element text directly."""
    if hasattr(element, "runs"):
        for r in element.runs:
            if r.text and search_str in r.text:
                r.text = r.text.replace(search_str, replace_str)
    else:
        try:
            if element.text:
                element.text = element.text.replace(search_str, replace_str)
        except Exception:
            pass


def substitute_spans_in_paragraph(paragraph, replacements: List[Dict]):
    """
    Replaces exact character index spans within a paragraph's runs while 
    maintaining run-level formatting. Evaluated from right to left (descending order) 
    to preserve index validity as text lengths change.
    """
    # Sort descending to apply right-to-left
    sorted_replacements = sorted(replacements, key=lambda item: item.get("start", 0), reverse=True)
    
    runs_list = collect_paragraph_runs(paragraph)
    if not runs_list:
        # Direct replacement on paragraph text if runs do not exist
        full_text = paragraph.text or ""
        for rep in sorted_replacements:
            start_pos = rep.get("start", 0)
            end_pos = rep.get("end", 0)
            sub_text = rep.get("replacement", "")
            full_text = full_text[:start_pos] + sub_text + full_text[end_pos:]
        paragraph.text = full_text
        return

    for rep in sorted_replacements:
        start_pos = rep.get("start", 0)
        end_pos = rep.get("end", 0)
        sub_text = rep.get("replacement", "")
        
        # Build character offsets for each run
        boundaries = []
        accumulated = 0
        for r in runs_list:
            text_len = len(r.text) if r.text else 0
            boundaries.append((accumulated, accumulated + text_len))
            accumulated += text_len
            
        max_limit = accumulated
        start_pos = max(0, min(start_pos, max_limit))
        end_pos = max(0, min(end_pos, max_limit))
        if start_pos >= end_pos:
            continue
            
        # Find which runs overlap with [start_pos, end_pos)
        overlapping_indexes = [
            idx for idx, (r_start, r_end) in enumerate(boundaries)
            if max(start_pos, r_start) < min(end_pos, r_end)
        ]
        
        if not overlapping_indexes:
            continue
            
        first_run_idx = overlapping_indexes[0]
        last_run_idx = overlapping_indexes[-1]
        
        target_first_run = runs_list[first_run_idx]
        first_start, first_end = boundaries[first_run_idx]
        
        if first_run_idx == last_run_idx:
            # Inline swap within a single run object
            pfx = target_first_run.text[:start_pos - first_start]
            sfx = target_first_run.text[end_pos - first_start:]
            target_first_run.text = pfx + sub_text + sfx
        else:
            target_last_run = runs_list[last_run_idx]
            last_start, last_end = boundaries[last_run_idx]
            
            pfx = target_first_run.text[:start_pos - first_start]
            sfx = target_last_run.text[end_pos - last_start:]
            
            target_first_run.text = pfx + sub_text
            
            # Wipe intermediate text
            for idx in overlapping_indexes[1:-1]:
                runs_list[idx].text = ""
                
            target_last_run.text = sfx


def apply_replacements(doc: Document, replacements: List[Dict]):
    """Applies replacements across all sections of the document (paragraphs, tables, cells)."""
    from extract import iter_text_blocks
    for p_element, _ in iter_text_blocks(doc):
        matched_items = []
        for rep in replacements:
            original_val = rep["original"]
            replacement_val = rep["replacement"]
            # Find index positions of original text in current paragraph
            for m in re.finditer(re.escape(original_val), p_element.text or ""):
                matched_items.append({
                    "start": m.start(),
                    "end": m.end(),
                    "replacement": replacement_val
                })
        if matched_items:
            substitute_spans_in_paragraph(p_element, matched_items)


def apply_replacements_to_container(container, replacements: List[Dict]):
    """Redacts PII inside a single paragraph/cell container object."""
    has_spans = all("start" in r and "end" in r for r in replacements)
    if has_spans:
        substitute_spans_in_paragraph(container, replacements)
    else:
        container_text = container.text or ""
        matched_items = []
        for rep in replacements:
            original_val = rep["original"]
            replacement_val = rep["replacement"]
            for m in re.finditer(re.escape(original_val), container_text):
                matched_items.append({
                    "start": m.start(),
                    "end": m.end(),
                    "replacement": replacement_val
                })
        if matched_items:
            substitute_spans_in_paragraph(container, matched_items)
        else:
            # Final fallback to standard replace
            for rep in replacements:
                fallback_text_replace(container, rep["original"], rep["replacement"])
