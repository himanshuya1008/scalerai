import argparse
import os
import sys
import re

try:
    from .extract import load_docx, iter_text_blocks
    from .detectors import detect_all, resolve_overlaps, _nlp, ner_detectors_from_doc, regex_detectors, merge_addresses
    from .anonymizer import Anonymizer
    from .writer import apply_replacements_to_container
    from .evaluator import evaluate, load_ground_truth
except ImportError:
    from extract import load_docx, iter_text_blocks
    from detectors import detect_all, resolve_overlaps, _nlp, ner_detectors_from_doc, regex_detectors, merge_addresses
    from anonymizer import Anonymizer
    from writer import apply_replacements_to_container
    from evaluator import evaluate, load_ground_truth


def collect_detections(doc_path: str):
    """
    Scans the document for PII using regex and spaCy NER in a high-performance batched pipeline.
    Uses a second-pass document-specific entity gazetteer to capture missed target occurrences.
    """
    doc_object = load_docx(doc_path)
    
    # Pass 1: Extract all blocks
    document_blocks = []
    for container, text_val in iter_text_blocks(doc_object):
        if not text_val or not text_val.strip():
            continue
        document_blocks.append({
            "container": container,
            "text": text_val,
            "dets": []
        })

    # Execute regex detection
    for block in document_blocks:
        block["dets"].extend(regex_detectors(block["text"]))

    # Execute spaCy NER in batch
    if _nlp is not None and document_blocks:
        all_texts = [b["text"] for b in document_blocks]
        compiled_docs = list(_nlp.pipe(all_texts, batch_size=256))
        for block, spacy_doc in zip(document_blocks, compiled_docs):
            block["dets"].extend(ner_detectors_from_doc(spacy_doc, block["text"]))

    # Process addresses and overlaps
    unique_persons_set = set()
    unique_companies_set = set()
    
    for block in document_blocks:
        merged_spans = merge_addresses(block["dets"], block["text"])
        block["dets"] = resolve_overlaps(merged_spans)
        
        # Populate document-specific gazetteer
        for d in block["dets"]:
            clean_txt = d["text"].strip()
            if len(clean_txt) > 2 and not clean_txt.isdigit():
                if d["type"] == "PERSON":
                    unique_persons_set.add(clean_txt)
                elif d["type"] == "COMPANY":
                    unique_companies_set.add(clean_txt)

    # Precompile regex search patterns for document entities
    regex_person_patterns = []
    for name in unique_persons_set:
        try:
            regex_person_patterns.append((name, re.compile(r"\b" + re.escape(name) + r"\b")))
        except Exception:
            pass

    regex_company_patterns = []
    for comp in unique_companies_set:
        try:
            regex_company_patterns.append((comp, re.compile(r"\b" + re.escape(comp) + r"\b")))
        except Exception:
            pass

    # Pass 2: Apply document-specific entity gazetteer
    final_output_detections = []
    for block in document_blocks:
        element_container = block["container"]
        element_text = block["text"]
        element_dets = list(block["dets"])
        
        # Match missed persons
        for name_val, compiled_regex in regex_person_patterns:
            for match in compiled_regex.finditer(element_text):
                is_overlapping = False
                for d in element_dets:
                    if max(match.start(), d["start"]) < min(match.end(), d["end"]):
                        is_overlapping = True
                        break
                if not is_overlapping:
                    element_dets.append({
                        "type": "PERSON",
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(0)
                    })
                    
        # Match missed companies
        for comp_val, compiled_regex in regex_company_patterns:
            for match in compiled_regex.finditer(element_text):
                is_overlapping = False
                for d in element_dets:
                    if max(match.start(), d["start"]) < min(match.end(), d["end"]):
                        is_overlapping = True
                        break
                if not is_overlapping:
                    element_dets.append({
                        "type": "COMPANY",
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(0)
                    })
                    
        resolved_elements = resolve_overlaps(element_dets)
        for d in resolved_elements:
            d["container_text"] = element_text
            d["container_obj"] = element_container
        final_output_detections.extend(resolved_elements)
        
    return doc_object, final_output_detections


def build_replacements_for_container(detections, anonymizer: Anonymizer):
    """Maps container objects to their respective replacements list."""
    mapping_dictionary = {}
    for d in detections:
        container_ref = d.get("container_obj")
        orig_text = d["text"]
        label_type = d["type"]
        pos_start = d.get("start")
        pos_end = d.get("end")
        
        fake_replacement = anonymizer.fake_for(label_type, orig_text)
        container_id = id(container_ref)
        
        mapping_dictionary.setdefault(container_id, {"container": container_ref, "replacements": []})["replacements"].append({
            "original": orig_text,
            "replacement": fake_replacement,
            "start": pos_start,
            "end": pos_end
        })
    return list(mapping_dictionary.values())


def main():
    cli_parser = argparse.ArgumentParser(description="PII Redactor Main Entry point.")
    cli_parser.add_argument("--input", required=True, help="Input DOCX path")
    cli_parser.add_argument("--output", required=True, help="Output DOCX path")
    cli_parser.add_argument("--ground_truth", required=False, help="Optional ground truth path")
    cli_args = cli_parser.parse_args()

    os.makedirs(os.path.dirname(cli_args.output) or ".", exist_ok=True)
    anonymizer_instance = Anonymizer(persist_path="output/mapping.json")
    
    doc_ref, found_pii = collect_detections(cli_args.input)
    container_replacements = build_replacements_for_container(found_pii, anonymizer_instance)
    
    # Redact document
    for item in container_replacements:
        apply_replacements_to_container(item["container"], item["replacements"])
        
    doc_ref.save(cli_args.output)
    anonymizer_instance.save()
    print(f"Redaction finished. Saved file to {cli_args.output}")

    if cli_args.ground_truth:
        gt_data = load_ground_truth(cli_args.ground_truth)
        evaluation_stats = evaluate(found_pii, gt_data)
        report_file_path = "reports/evaluation_report.md"
        os.makedirs(os.path.dirname(report_file_path), exist_ok=True)
        
        with open(report_file_path, "w", encoding="utf-8") as out_stream:
            out_stream.write("# PII Redaction Evaluation Report\n\n")
            out_stream.write("## Executive Summary\n\n")
            out_stream.write("Evaluation analysis of PII redactions against ground-truth labels.\n\n")
            out_stream.write("> [!NOTE]\n")
            out_stream.write("> Accuracy is calculated over detected instances. Precision and Recall are primary metrics.\n\n")
            
            out_stream.write("## Overall Metrics\n\n")
            out_stream.write(f"- **True Positives (TP)**: {evaluation_stats.get('tp')}\n")
            out_stream.write(f"- **False Positives (FP)**: {evaluation_stats.get('fp')}\n")
            out_stream.write(f"- **False Negatives (FN)**: {evaluation_stats.get('fn')}\n")
            out_stream.write(f"- **Precision**: {evaluation_stats.get('precision'):.3f}\n")
            out_stream.write(f"- **Recall**: {evaluation_stats.get('recall'):.3f}\n")
            out_stream.write(f"- **F1-Score**: {evaluation_stats.get('f1'):.3f}\n")
            out_stream.write(f"- **Accuracy**: {evaluation_stats.get('accuracy'):.3f}\n\n")
            
            out_stream.write("## Per-Category Metrics\n\n")
            out_stream.write("| PII Category | TP | FP | FN | Precision | Recall | F1-Score | Accuracy |\n")
            out_stream.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
            for label, val in evaluation_stats.get("per_type", {}).items():
                out_stream.write(f"| {label} | {val.get('tp',0)} | {val.get('fp',0)} | {val.get('fn',0)} | {val.get('precision',0.0):.3f} | {val.get('recall',0.0):.3f} | {val.get('f1',0.0):.3f} | {val.get('accuracy',0.0):.3f} |\n")
            
            out_stream.write("\n## Error Analysis\n\n")
            out_stream.write("### False Positives\n")
            fp_list = [d for d in found_pii if not any(d["text"].strip().lower() in g["text"].strip().lower() for g in gt_data)]
            if fp_list:
                for fp_item in fp_list[:5]:
                    out_stream.write(f"- Detected `{fp_item['text']}` as `{fp_item['type']}`\n")
            else:
                out_stream.write("- None.\n")
                
            out_stream.write("\n### False Negatives\n")
            matched_gt_flags = [False] * len(gt_data)
            from evaluator import is_fuzzy_match
            for d in found_pii:
                for idx, g in enumerate(gt_data):
                    if not matched_gt_flags[idx] and is_fuzzy_match(d.get("text", ""), d.get("type", ""), g.get("text", ""), g.get("type", "")):
                        matched_gt_flags[idx] = True
                        break
            fn_list = [g for idx, g in enumerate(gt_data) if not matched_gt_flags[idx]]
            if fn_list:
                for fn_item in fn_list[:5]:
                    out_stream.write(f"- Missed `{fn_item['text']}` of type `{fn_item['type']}`\n")
            else:
                out_stream.write("- None.\n")

        print(f"Evaluation report written to {report_file_path}")


if __name__ == "__main__":
    main()
