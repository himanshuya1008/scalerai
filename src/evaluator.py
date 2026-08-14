import json
from typing import List, Dict


def load_ground_truth(file_path: str) -> List[Dict]:
    """Loads and normalizes ground truth PII labels from JSON."""
    with open(file_path, "r", encoding="utf-8") as file_stream:
        labels_list = json.load(file_stream)
    
    # Map incoming alternative names to standard target keys
    label_normalize_map = {
        "NAME": "PERSON",
        "IP": "IP_ADDRESS",
        "DATE": "DOB"
    }
    
    for item in labels_list:
        lbl = item.get("type", "")
        if lbl in label_normalize_map:
            item["type"] = label_normalize_map[lbl]
            
    return labels_list


def is_fuzzy_match(detected_text: str, detected_type: str, gt_text: str, gt_type: str) -> bool:
    """Verifies if a detected item matches a ground-truth item based on type and content overlap."""
    if detected_type != gt_type:
        return False
    
    val_a = detected_text.strip().lower()
    val_b = gt_text.strip().lower()
    
    # Return true if exact match or either is substring of the other
    return val_a == val_b or val_a in val_b or val_b in val_a


def evaluate(detections: List[Dict], ground_truth: List[Dict]) -> Dict:
    """
    Computes Precision, Recall, F1-Score, and Accuracy of PII detections 
    against the ground truth using overlap text matching.
    """
    ground_truth_matched_mask = [False] * len(ground_truth)
    total_tp = 0
    total_fp = 0
    total_fn = 0
    
    category_map = {}
    standard_categories = ["PERSON", "EMAIL", "PHONE", "COMPANY", "ADDRESS", "SSN", "CREDIT_CARD", "DOB", "IP_ADDRESS"]
    for cat in standard_categories:
        category_map[cat] = {"tp": 0, "fp": 0, "fn": 0}

    for d in detections:
        is_matched = False
        d_type = d.get("type", "")
        if d_type not in category_map:
            category_map[d_type] = {"tp": 0, "fp": 0, "fn": 0}
            
        for idx, gt_item in enumerate(ground_truth):
            if not ground_truth_matched_mask[idx]:
                if is_fuzzy_match(d.get("text", ""), d_type, gt_item.get("text", ""), gt_item.get("type", "")):
                    is_matched = True
                    ground_truth_matched_mask[idx] = True
                    total_tp += 1
                    category_map[d_type]["tp"] += 1
                    break
                    
        if not is_matched:
            total_fp += 1
            category_map[d_type]["fp"] += 1

    for idx, matched in enumerate(ground_truth_matched_mask):
        if not matched:
            total_fn += 1
            gt_item = ground_truth[idx]
            gt_type = gt_item.get("type", "")
            if gt_type not in category_map:
                category_map[gt_type] = {"tp": 0, "fp": 0, "fn": 0}
            category_map[gt_type]["fn"] += 1

    # Calculation logic with customized variable names
    pr_divisor = total_tp + total_fp
    overall_precision = float(total_tp) / pr_divisor if pr_divisor > 0 else 0.0
    
    rec_divisor = total_tp + total_fn
    overall_recall = float(total_tp) / rec_divisor if rec_divisor > 0 else 0.0
    
    f1_divisor = overall_precision + overall_recall
    overall_f1 = (2.0 * overall_precision * overall_recall) / f1_divisor if f1_divisor > 0 else 0.0
    
    acc_divisor = total_tp + total_fp + total_fn
    overall_accuracy = float(total_tp) / acc_divisor if acc_divisor > 0 else 0.0

    # Compile per-category statistics
    category_metrics = {}
    for cat_name, stats in category_map.items():
        tp_val = stats["tp"]
        fp_val = stats["fp"]
        fn_val = stats["fn"]
        
        prec = float(tp_val) / (tp_val + fp_val) if (tp_val + fp_val) > 0 else 0.0
        rec = float(tp_val) / (tp_val + fn_val) if (tp_val + fn_val) > 0 else 0.0
        f1_val = (2.0 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        acc_val = float(tp_val) / (tp_val + fp_val + fn_val) if (tp_val + fp_val + fn_val) > 0 else 0.0
        
        category_metrics[cat_name] = {
            "tp": tp_val,
            "fp": fp_val,
            "fn": fn_val,
            "precision": prec,
            "recall": rec,
            "f1": f1_val,
            "accuracy": acc_val
        }

    return {
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
        "precision": overall_precision,
        "recall": overall_recall,
        "f1": overall_f1,
        "accuracy": overall_accuracy,
        "per_type": category_metrics
    }
