import json
from typing import List, Dict


def load_ground_truth(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Normalize ground truth types to match detector types
    type_mapping = {
        "NAME": "PERSON",
        "IP": "IP_ADDRESS",
        "DATE": "DOB"
    }
    for item in data:
        t = item.get("type", "")
        if t in type_mapping:
            item["type"] = type_mapping[t]
            
    return data


def _matches(detect_text: str, detect_type: str, gt_text: str, gt_type: str) -> bool:
    if detect_type != gt_type:
        return False
    a = detect_text.strip().lower()
    b = gt_text.strip().lower()
    # exact or substring match
    if a == b or a in b or b in a:
        return True
    return False


def evaluate(detections: List[Dict], ground_truth: List[Dict]) -> Dict:
    """Evaluate using fuzzy/text overlap matching. Returns per-type and overall metrics."""
    gt_used = [False] * len(ground_truth)
    tp = 0
    fp = 0
    fn = 0
    per_type = {}

    # Initialize per-type dictionary for all known categories
    all_categories = ["PERSON", "EMAIL", "PHONE", "COMPANY", "ADDRESS", "SSN", "CREDIT_CARD", "DOB", "IP_ADDRESS"]
    for cat in all_categories:
        per_type[cat] = {"tp": 0, "fp": 0, "fn": 0}

    for d in detections:
        matched = False
        d_type = d.get("type", "")
        if d_type not in per_type:
            per_type[d_type] = {"tp": 0, "fp": 0, "fn": 0}
            
        for i, g in enumerate(ground_truth):
            if _matches(d.get("text", ""), d_type, g.get("text", ""), g.get("type", "")) and not gt_used[i]:
                matched = True
                gt_used[i] = True
                tp += 1
                per_type[d_type]["tp"] += 1
                break
        if not matched:
            fp += 1
            per_type[d_type]["fp"] += 1

    for i, used in enumerate(gt_used):
        if not used:
            fn += 1
            g = ground_truth[i]
            g_type = g.get("type", "")
            if g_type not in per_type:
                per_type[g_type] = {"tp": 0, "fp": 0, "fn": 0}
            per_type[g_type]["fn"] += 1

    # Calculate overall metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0

    # Calculate per-type metrics
    per_type_metrics = {}
    for t, vals in per_type.items():
        t_tp = vals["tp"]
        t_fp = vals["fp"]
        t_fn = vals["fn"]
        t_prec = t_tp / (t_tp + t_fp) if (t_tp + t_fp) > 0 else 0.0
        t_rec = t_tp / (t_tp + t_fn) if (t_tp + t_fn) > 0 else 0.0
        t_f1 = 2 * t_prec * t_rec / (t_prec + t_rec) if (t_prec + t_rec) > 0 else 0.0
        t_acc = t_tp / (t_tp + t_fp + t_fn) if (t_tp + t_fp + t_fn) > 0 else 0.0
        
        per_type_metrics[t] = {
            "tp": t_tp,
            "fp": t_fp,
            "fn": t_fn,
            "precision": t_prec,
            "recall": t_rec,
            "f1": t_f1,
            "accuracy": t_acc
        }

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "per_type": per_type_metrics
    }
