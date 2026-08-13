from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import uuid
from werkzeug.utils import secure_filename

try:
    from .main import collect_detections, build_replacements_for_container
    from .anonymizer import Anonymizer
    from .writer import apply_replacements_to_container
except ImportError:
    from main import collect_detections, build_replacements_for_container
    from anonymizer import Anonymizer
    from writer import apply_replacements_to_container

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'input')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


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

    anonymizer = Anonymizer(persist_path=os.path.join(OUTPUT_FOLDER, 'mapping.json'))
    doc, detections = collect_detections(in_path)
    container_reps = build_replacements_for_container(detections, anonymizer)
    # apply replacements per container
    for item in container_reps:
        apply_replacements_to_container(item['container'], item['replacements'])
    out_path = os.path.join(OUTPUT_FOLDER, f"redacted_{safe_name}")
    doc.save(out_path)
    anonymizer.save()
    return send_file(out_path, as_attachment=True)


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
