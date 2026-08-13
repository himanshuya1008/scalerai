import argparse
import os
from extract import load_docx, iter_text_blocks
from detectors import detect_all
from anonymizer import Anonymizer
from writer import apply_replacements, apply_replacements_to_container
from evaluator import evaluate, load_ground_truth


def collect_detections(doc_path: str):
    doc = load_docx(doc_path)
    detections = []
    # detect per-container to keep spans clean and enable precise replacements
    for container, text in iter_text_blocks(doc):
        if not text or text.strip() == "":
            continue
        dets = detect_all(text)
        # attach container reference to each detection
        for d in dets:
            d["container_text"] = text
            d["container_obj"] = container
        detections.extend(dets)
    return doc, detections


def build_replacements_for_container(detections, anonymizer: Anonymizer):
    """Group detections by their container and return mapping container -> replacements list."""
    container_map = {}
    for d in detections:
        container = d.get("container_obj")
        original = d["text"]
        ent_type = d["type"]
        fake = anonymizer.fake_for(ent_type, original)
        container_map.setdefault(id(container), {"container": container, "replacements": []})["replacements"].append({"original": original, "replacement": fake})
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
            f.write("# Evaluation Report\n\n")
            f.write("## Summary\n\n")
            f.write(f"- True positives: {stats.get('tp')}\n")
            f.write(f"- False positives: {stats.get('fp')}\n")
            f.write(f"- False negatives: {stats.get('fn')}\n")
            f.write(f"- Precision: {stats.get('precision'):.3f}\n")
            f.write(f"- Recall: {stats.get('recall'):.3f}\n")
            f.write(f"- F1: {stats.get('f1'):.3f}\n\n")
            f.write("## Per-type metrics\n\n")
            f.write("| PII Type | TP | FP | FN |\n")
            f.write("|---|---:|---:|---:|\n")
            for t, vals in stats.get("per_type", {}).items():
                f.write(f"| {t} | {vals.get('tp',0)} | {vals.get('fp',0)} | {vals.get('fn',0)} |\n")

        print(f"Evaluation written to {report_path}")


if __name__ == "__main__":
    main()
