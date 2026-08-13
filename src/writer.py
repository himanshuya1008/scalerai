from docx import Document
from typing import List, Dict


def get_all_runs(paragraph) -> list:
    """Recursively collect all Run objects under the paragraph element in document order,
    including nested runs (like those inside hyperlinks)."""
    runs = []
    def recurse(element):
        for child in element:
            tag = child.tag.split('}')[-1]
            if tag == 'r':
                from docx.text.run import Run
                runs.append(Run(child, paragraph))
            else:
                recurse(child)
    recurse(paragraph._element)
    return runs


def replace_in_run_obj(container, original: str, replacement: str):
    """Old global string replace fallback."""
    if hasattr(container, "runs"):
        for run in container.runs:
            if original in run.text:
                run.text = run.text.replace(original, replacement)
    else:
        try:
            container.text = container.text.replace(original, replacement)
        except Exception:
            pass


def apply_span_replacements(paragraph, replacements: List[Dict]):
    """Apply multiple span-based replacements to a paragraph, maintaining formatting."""
    # Sort replacements by start index descending to apply them right-to-left.
    # This ensures that changes to run lengths do not invalidate subsequent index offsets to the left.
    sorted_reps = sorted(replacements, key=lambda x: x.get("start", 0), reverse=True)
    
    runs = get_all_runs(paragraph)
    if not runs:
        # Fallback to paragraph.text replacement if there are no runs
        text = paragraph.text
        for rep in sorted_reps:
            start = rep.get("start", 0)
            end = rep.get("end", 0)
            replacement = rep.get("replacement", "")
            text = text[:start] + replacement + text[end:]
        paragraph.text = text
        return

    for rep in sorted_reps:
        start = rep.get("start", 0)
        end = rep.get("end", 0)
        replacement = rep.get("replacement", "")
        
        # Calculate run character offsets in the paragraph text
        run_offsets = []
        current_offset = 0
        for r in runs:
            r_text = r.text or ""
            run_offsets.append((current_offset, current_offset + len(r_text)))
            current_offset += len(r_text)
            
        total_len = current_offset
        # Safeguard start/end boundaries
        start = max(0, min(start, total_len))
        end = max(0, min(end, total_len))
        if start >= end:
            continue
            
        # Find which runs overlap with [start, end)
        overlapping_indices = []
        for idx, (r_start, r_end) in enumerate(run_offsets):
            if max(start, r_start) < min(end, r_end):
                overlapping_indices.append(idx)
                
        if not overlapping_indices:
            continue
            
        first_idx = overlapping_indices[0]
        last_idx = overlapping_indices[-1]
        
        first_run = runs[first_idx]
        first_r_start, first_r_end = run_offsets[first_idx]
        
        if first_idx == last_idx:
            # Replacement is entirely within one run
            prefix = first_run.text[:start - first_r_start]
            suffix = first_run.text[end - first_r_start:]
            first_run.text = prefix + replacement + suffix
        else:
            last_run = runs[last_idx]
            last_r_start, last_r_end = run_offsets[last_idx]
            
            prefix = first_run.text[:start - first_r_start]
            suffix = last_run.text[end - last_r_start:]
            
            first_run.text = prefix + replacement
            
            # Clear text of intermediate runs
            for idx in overlapping_indices[1:-1]:
                runs[idx].text = ""
                
            last_run.text = suffix


def apply_replacements(doc: Document, replacements: List[Dict]):
    """Apply replacements across entire document. Keep signature for compatibility."""
    # We yield all paragraphs across body, headers, footers, tables and apply
    from extract import iter_text_blocks
    # Group replacements by container if they aren't already
    # For compatibility, this might be a simple original-to-replacement list
    for p, _text in iter_text_blocks(doc):
        # Find matches of rep['original'] in p.text
        local_reps = []
        for rep in replacements:
            orig = rep["original"]
            repl = rep["replacement"]
            # Find all occurrences of orig in p.text
            for match in re.finditer(re.escape(orig), p.text):
                local_reps.append({
                    "start": match.start(),
                    "end": match.end(),
                    "replacement": repl
                })
        if local_reps:
            apply_span_replacements(p, local_reps)


def apply_replacements_to_container(container, replacements: List[Dict]):
    """Apply list of replacements to a single paragraph container."""
    has_spans = all("start" in r and "end" in r for r in replacements)
    if has_spans:
        apply_span_replacements(container, replacements)
    else:
        # If no spans, find occurrences of original text in container.text and map them to spans
        text = container.text
        local_reps = []
        for rep in replacements:
            orig = rep["original"]
            repl = rep["replacement"]
            for match in re.finditer(re.escape(orig), text):
                local_reps.append({
                    "start": match.start(),
                    "end": match.end(),
                    "replacement": repl
                })
        if local_reps:
            apply_span_replacements(container, local_reps)
        else:
            # Absolute fallback
            for rep in replacements:
                replace_in_run_obj(container, rep["original"], rep["replacement"])
