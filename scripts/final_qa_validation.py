import os
import sys
import json

try:
    from src.main import collect_detections, build_replacements_for_container
    from src.anonymizer import Anonymizer
    from src.writer import apply_replacements_to_container
    from src.evaluator import evaluate, load_ground_truth
    from src.detectors import detect_all
except ImportError:
    # Adjust python path if necessary
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from src.main import collect_detections, build_replacements_for_container
    from src.anonymizer import Anonymizer
    from src.writer import apply_replacements_to_container
    from src.evaluator import evaluate, load_ground_truth
    from src.detectors import detect_all


def run_redaction(in_path: str, out_path: str, mapping_path: str):
    """Run full redaction pipeline and save result."""
    anonymizer = Anonymizer(persist_path=mapping_path)
    doc, detections = collect_detections(in_path)
    container_reps = build_replacements_for_container(detections, anonymizer)
    
    for item in container_reps:
        apply_replacements_to_container(item["container"], item["replacements"])
        
    doc.save(out_path)
    anonymizer.save()
    return detections


def scan_output(doc_path: str):
    """Scan output document for remaining PII (second-pass validation)."""
    _, detections = collect_detections(doc_path)
    return detections


def main():
    print("--- Starting Final QA Verification ---\n")
    
    # Paths
    small_in = "input/de2ccf76088e4d4c8144438749680c0a_PII_Redaction_Test_Input_1.docx"
    small_out = "output/Redacted_PII_Test_Output.docx"
    large_in = "input/Red Herring Prospectus.docx"
    large_out = "output/Redacted_Red_Herring_Prospectus.docx"
    
    # 1. Run redaction on small test document
    print(f"Redacting small synthetic doc: {small_in} ...")
    small_orig_dets = run_redaction(small_in, small_out, "output/mapping_small.json")
    print(f"Detected {len(small_orig_dets)} PII entities initially.")
    
    # 2. Run redaction on large Red Herring Prospectus
    print(f"\nRedacting large prospectus: {large_in} ...")
    large_orig_dets = run_redaction(large_in, large_out, "output/mapping_large.json")
    print(f"Detected {len(large_orig_dets)} PII entities initially.")
    
    # 3. Second-pass validation
    print("\n--- Running Second-Pass Validation ---")
    small_remaining = scan_output(small_out)
    print(f"Small doc remaining PII counts: {len(small_remaining)}")
    if small_remaining:
        print("Warning! Remaining detections in small doc:")
        for r in small_remaining:
            print(f" - {r['type']}: {r['text']}")
            
    large_remaining = scan_output(large_out)
    print(f"Large doc remaining PII counts: {len(large_remaining)}")
    if large_remaining:
        print("Warning! Remaining detections in large doc:")
        # Show first 10 for log checking
        for r in large_remaining[:10]:
            print(f" - {r['type']}: {r['text']}")
            
    # 4. Load ground truth and evaluate metrics
    print("\n--- Evaluating Metrics against Ground Truth ---")
    gt = load_ground_truth("tests/ground_truth.json")
    # Evaluate using the sample.docx redaction
    sample_in = "input/sample.docx"
    sample_out = "output/redacted.docx"
    sample_dets = run_redaction(sample_in, sample_out, "output/mapping.json")
    stats = evaluate(sample_dets, gt)
    
    print(f"Overall Accuracy: {stats.get('accuracy'):.3f}")
    print(f"Overall Precision: {stats.get('precision'):.3f}")
    print(f"Overall Recall: {stats.get('recall'):.3f}")
    print(f"Overall F1-Score: {stats.get('f1'):.3f}")
    
    # Generate final report file
    qa_report_path = "reports/final_qa_report.md"
    os.makedirs(os.path.dirname(qa_report_path), exist_ok=True)
    with open(qa_report_path, "w", encoding="utf-8") as f:
        f.write("# Final QA Verification Report\n\n")
        f.write("## Overview\n\n")
        f.write("This report documents the final QA validation, covering the second-pass scan verification of the redacted documents and evaluation metrics against the ground truth dataset.\n\n")
        
        f.write("## 1. Ground Truth Evaluation Metrics\n\n")
        f.write(f"- **Overall Accuracy**: {stats.get('accuracy'):.3f}\n")
        f.write(f"- **Overall Precision**: {stats.get('precision'):.3f}\n")
        f.write(f"- **Overall Recall**: {stats.get('recall'):.3f}\n")
        f.write(f"- **Overall F1-Score**: {stats.get('f1'):.3f}\n\n")
        
        f.write("### Per-Category Metrics\n\n")
        f.write("| PII Category | TP | FP | FN | Precision | Recall | F1-Score | Accuracy |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for t, vals in stats.get("per_type", {}).items():
            f.write(f"| {t} | {vals.get('tp',0)} | {vals.get('fp',0)} | {vals.get('fn',0)} | {vals.get('precision',0.0):.3f} | {vals.get('recall',0.0):.3f} | {vals.get('f1',0.0):.3f} | {vals.get('accuracy',0.0):.3f} |\n")
            
        f.write("\n## 2. Second-Pass Validation Scan\n\n")
        f.write("| Document | Initial Detections | Remaining PII (Second-Pass) | Status |\n")
        f.write("|---|---:|---:|---:|\n")
        small_status = "PASS" if len(small_remaining) == 0 else "FAIL"
        large_status = "PASS" if len(large_remaining) == 0 else "WARNING"
        f.write(f"| Synthetic Test Doc | {len(small_orig_dets)} | {len(small_remaining)} | {small_status} |\n")
        f.write(f"| Red Herring Prospectus | {len(large_orig_dets)} | {len(large_remaining)} | {large_status} |\n\n")
        
        if large_remaining:
            f.write("### Remaining Detections in Large Document (Sample)\n")
            for r in large_remaining[:15]:
                f.write(f"- `{r['type']}`: `{r['text']}`\n")
                
    print(f"\nFinal QA Report written to {qa_report_path}")


if __name__ == "__main__":
    main()
