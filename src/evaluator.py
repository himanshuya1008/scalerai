import json
from typing import List, Dict


def load_ground_truth(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
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

    for d in detections:
        matched = False
        for i, g in enumerate(ground_truth):
            if _matches(d.get("text", ""), d.get("type", ""), g.get("text", ""), g.get("type", "")) and not gt_used[i]:
                matched = True
                gt_used[i] = True
                tp += 1
                per_type.setdefault(d.get("type"), {"tp": 0, "fp": 0, "fn": 0})
                per_type[d.get("type")]["tp"] += 1
                break
        if not matched:
            fp += 1
            per_type.setdefault(d.get("type"), {"tp": 0, "fp": 0, "fn": 0})
            per_type[d.get("type")]["fp"] += 1

    for i, used in enumerate(gt_used):
        if not used:
            fn += 1
            g = ground_truth[i]
            per_type.setdefault(g.get("type"), {"tp": 0, "fp": 0, "fn": 0})
            per_type[g.get("type")]["fn"] += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1, "per_type": per_type}
