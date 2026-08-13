import argparse
import os
import sys
import re

try:
    from .extract import load_docx, iter_text_blocks
    from .detectors import detect_all, resolve_overlaps
    from .anonymizer import Anonymizer
    from .writer import apply_replacements_to_container
    from .evaluator import evaluate, load_ground_truth
except ImportError:
    from extract import load_docx, iter_text_blocks
    from detectors import detect_all, resolve_overlaps
    from anonymizer import Anonymizer
    from writer import apply_replacements_to_container
    from evaluator import evaluate, load_ground_truth


def collect_detections(doc_path: str):
    doc = load_docx(doc_path)
    
    # First pass: collect initial detections and record blocks
    first_pass_detections = []
    blocks = []
    for container, text in iter_text_blocks(doc):
        if not text or text.strip() == "":
            continue
        dets = detect_all(text)
        first_pass_detections.extend(dets)
        blocks.append((container, text))
        
    # Extract unique Person and Company entities detected with high confidence
    known_persons = set()
    known_companies = set()
    for d in first_pass_detections:
        txt = d["text"].strip()
        # Avoid very short strings or numeric noise
        if len(txt) > 2 and not txt.isdigit():
            if d["type"] == "PERSON":
                known_persons.add(txt)
            elif d["type"] == "COMPANY":
                known_companies.add(txt)
                
    # Second pass: re-scan and apply the document-specific entity gazetteer
    final_detections = []
    for container, text in blocks:
        dets = detect_all(text)
        
        # Check for missed occurrences of known persons
        for name in known_persons:
            for m in re.finditer(r"\b" + re.escape(name) + r"\b", text):
                # Ensure no overlap with existing detections
                overlap = False
                for d in dets:
                    if max(m.start(), d["start"]) < min(m.end(), d["end"]):
                        overlap = True
                        break
                if not overlap:
                    dets.append({
                        "type": "PERSON",
                        "start": m.start(),
                        "end": m.end(),
                        "text": m.group(0)
                    })
                    
        # Check for missed occurrences of known companies
        for comp in known_companies:
            for m in re.finditer(r"\b" + re.escape(comp) + r"\b", text):
                overlap = False
                for d in dets:
                    if max(m.start(), d["start"]) < min(m.end(), d["end"]):
                        overlap = True
                        break
                if not overlap:
                    dets.append({
                        "type": "COMPANY",
                        "start": m.start(),
                        "end": m.end(),
                        "text": m.group(0)
                    })
                    
        # Resolve overlaps again
        resolved = resolve_overlaps(dets)
        for d in resolved:
            d["container_text"] = text
            d["container_obj"] = container
        final_detections.extend(resolved)
        
    return doc, final_detections


def build_replacements_for_container(detections, anonymizer: Anonymizer):
    """Group detections by their container and return mapping container -> replacements list."""
    container_map = {}
    for d in detections:
        container = d.get("container_obj")
        original = d["text"]
        ent_type = d["type"]
        start = d.get("start")
        end = d.get("end")
        fake = anonymizer.fake_for(ent_type, original)
        container_map.setdefault(id(container), {"container": container, "replacements": []})["replacements"].append({
            "original": original,
            "replacement": fake,
            "start": start,
            "end": end
        })
    return list(container_map.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ground_truth", required=False)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    anonymizer = Anonymizer(persist_path="output/mapping.json")
    doc, detections = collect_detections(args.input)
    container_reps = build_replacements_for_container(detections, anonymizer)
    
    # apply per-container replacements
    for item in container_reps:
        apply_replacements_to_container(item["container"], item["replacements"])
        
    doc.save(args.output)
    anonymizer.save()
    print(f"Saved redacted docx to {args.output}")

    if args.ground_truth:
        gt = load_ground_truth(args.ground_truth)
        stats = evaluate(detections, gt)
        report_path = "reports/evaluation_report.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# PII Redaction Evaluation Report\n\n")
            
            f.write("## Executive Summary\n\n")
            f.write("This report evaluates the accuracy and quality of the PII Redaction Tool against ground-truth annotations.\n\n")
            f.write("> [!NOTE]\n")
            f.write("> Accuracy can be misleading for PII detection because PII is highly sparse in natural language documents. ")
            f.write("For this reason, **Precision** and **Recall** are the most critical metrics for assessing redaction performance.\n\n")
            
            f.write("## Overall Metrics\n\n")
            f.write(f"- **True Positives (TP)**: {stats.get('tp')}\n")
            f.write(f"- **False Positives (FP)**: {stats.get('fp')}\n")
            f.write(f"- **False Negatives (FN)**: {stats.get('fn')}\n")
            f.write(f"- **Precision**: {stats.get('precision'):.3f}\n")
            f.write(f"- **Recall**: {stats.get('recall'):.3f}\n")
            f.write(f"- **F1-Score**: {stats.get('f1'):.3f}\n")
            f.write(f"- **Accuracy**: {stats.get('accuracy'):.3f}\n\n")
            
            f.write("## Per-Category Metrics\n\n")
            f.write("| PII Category | TP | FP | FN | Precision | Recall | F1-Score | Accuracy |\n")
            f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
            for t, vals in stats.get("per_type", {}).items():
                f.write(f"| {t} | {vals.get('tp',0)} | {vals.get('fp',0)} | {vals.get('fn',0)} | {vals.get('precision',0.0):.3f} | {vals.get('recall',0.0):.3f} | {vals.get('f1',0.0):.3f} | {vals.get('accuracy',0.0):.3f} |\n")
            
            f.write("\n## Error Analysis\n\n")
            f.write("### False Positives\n")
            f.write("Occurrences where the model detected non-PII values or wrong PII types:\n")
            fps = [d for d in detections if not any(d["text"].strip().lower() in g["text"].strip().lower() for g in gt)]
            if fps:
                for fp_det in fps[:5]:
                    f.write(f"- Detected `{fp_det['text']}` as `{fp_det['type']}`\n")
            else:
                f.write("- None detected.\n")
                
            f.write("\n### False Negatives\n")
            f.write("Occurrences where the model missed ground-truth PII values:\n")
            gt_used = [False] * len(gt)
            from evaluator import _matches
            for d in detections:
                for i, g in enumerate(gt):
                    if _matches(d.get("text", ""), d.get("type", ""), g.get("text", ""), g.get("type", "")) and not gt_used[i]:
                        gt_used[i] = True
                        break
            fns = [g for idx, g in enumerate(gt) if not gt_used[idx]]
            if fns:
                for fn_item in fns[:5]:
                    f.write(f"- Missed `{fn_item['text']}` of type `{fn_item['type']}`\n")
            else:
                f.write("- None missed.\n")

        print(f"Evaluation report written to {report_path}")


if __name__ == "__main__":
    main()
