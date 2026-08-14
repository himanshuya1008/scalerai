from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import uuid
import json
from werkzeug.utils import secure_filename

try:
    from .main import collect_detections, build_replacements_for_container
    from .anonymizer import Anonymizer
    from .writer import apply_replacements_to_container
    from .evaluator import evaluate
except ImportError:
    from main import collect_detections, build_replacements_for_container
    from anonymizer import Anonymizer
    from writer import apply_replacements_to_container
    from evaluator import evaluate

app = Flask(__name__)

DEFAULT_CORS_ORIGINS = '*'
cors_origins = [o.strip() for o in os.getenv('CORS_ORIGINS', DEFAULT_CORS_ORIGINS).split(',') if o.strip()]

# Configure CORS to expose custom metadata headers to the frontend
CORS(app, resources={r"/*": {
    "origins": cors_origins,
    "expose_headers": [
        "X-Entities-Detected",
        "X-Entities-Redacted",
        "X-Category-Breakdown",
        "X-Precision",
        "X-Recall",
        "X-F1",
        "X-Accuracy",
        "X-Has-Evaluation"
    ]
}})

max_upload_mb = int(os.getenv('MAX_UPLOAD_MB', '25'))
app.config['MAX_CONTENT_LENGTH'] = max_upload_mb * 1024 * 1024

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'input')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({'error': f'file exceeds {max_upload_mb}MB limit'}), 413


@app.route('/upload', methods=['POST'])
def upload_and_redact():
    if 'file' not in request.files:
        return jsonify({'error': 'no file part'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'no selected file'}), 400
    safe_name = secure_filename(f.filename)
    if not safe_name.lower().endswith('.docx'):
        return jsonify({'error': 'only .docx files are supported'}), 400

    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    in_path = os.path.join(UPLOAD_FOLDER, unique_name)
    f.save(in_path)

    # Check for optional ground_truth file upload
    gt_list = None
    if 'ground_truth' in request.files:
        gt_f = request.files['ground_truth']
        if gt_f.filename != '':
            try:
                # Map TYPE naming conventions
                type_mapping = {
                    "NAME": "PERSON",
                    "IP": "IP_ADDRESS",
                    "DATE": "DOB"
                }
                raw_gt = json.load(gt_f)
                for item in raw_gt:
                    t = item.get("type", "")
                    if t in type_mapping:
                        item["type"] = type_mapping[t]
                gt_list = raw_gt
            except Exception as e:
                print(f"Error parsing ground truth: {e}")

    anonymizer = Anonymizer(persist_path=os.path.join(OUTPUT_FOLDER, 'mapping.json'))
    doc, detections = collect_detections(in_path)
    container_reps = build_replacements_for_container(detections, anonymizer)
    
    # apply replacements per container
    for item in container_reps:
        apply_replacements_to_container(item['container'], item['replacements'])
        
    out_path = os.path.join(OUTPUT_FOLDER, f"redacted_{safe_name}")
    doc.save(out_path)
    anonymizer.save()

    # Calculate breakdown
    counts = {}
    for d in detections:
        t = d['type']
        counts[t] = counts.get(t, 0) + 1

    response = send_file(out_path, as_attachment=True)
    response.headers['X-Entities-Detected'] = str(len(detections))
    response.headers['X-Entities-Redacted'] = str(len(detections))
    response.headers['X-Category-Breakdown'] = json.dumps(counts)

    # Perform evaluation if ground truth is supplied
    if gt_list is not None:
        try:
            stats = evaluate(detections, gt_list)
            response.headers['X-Has-Evaluation'] = 'true'
            response.headers['X-Precision'] = f"{stats.get('precision', 0.0):.3f}"
            response.headers['X-Recall'] = f"{stats.get('recall', 0.0):.3f}"
            response.headers['X-F1'] = f"{stats.get('f1', 0.0):.3f}"
            response.headers['X-Accuracy'] = f"{stats.get('accuracy', 0.0):.3f}"
        except Exception as e:
            print(f"Error during API evaluation: {e}")
            response.headers['X-Has-Evaluation'] = 'false'
    else:
        response.headers['X-Has-Evaluation'] = 'false'

    return response


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok', 'max_upload_mb': max_upload_mb})


if __name__ == '__main__':
    debug_enabled = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    port = int(os.getenv('PORT', '8000'))
    app.run(host='0.0.0.0', port=port, debug=debug_enabled)
