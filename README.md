# PII Redaction Tool

PII Redaction Tool — professionalized

Overview

This project implements a hybrid PII detection and anonymization pipeline for DOCX documents. It combines deterministic regex detectors (email, phone, IP, SSN, credit card, dates) with spaCy NER (names, organizations, locations). Replacements use `faker` and are persisted so repeated occurrences map to the same pseudonym.

What I improved

- Per-container detection (paragraphs / table cells / headers) to avoid run-splitting replacement issues.
- Smarter detectors: Luhn validation for credit cards, stricter phone validation, improved date regex, and NER filters for PERSON/ORG/ADDRESS to reduce false positives.
- Evaluation: fuzzy matching (substring overlap) and per-type metrics with a human-friendly markdown report.

Quick start

1. Create a Python venv and install requirements:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1   # or .venv\Scripts\activate for cmd
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

2. Run the redactor on a file (example):

```powershell
python src/main.py --input "input/Red Herring Prospectus.docx" --output "output/redacted.docx" --ground_truth tests/ground_truth.json
```

3. Run the web app locally:

```powershell
# Terminal 1 (API)
python src/api.py

# Terminal 2 (frontend)
cd frontend
npm install --include=optional
npm start
```

If port 3000 is already occupied, Vite will automatically use the next available port (for example, 3001).

4. Launch backend + frontend together (Windows PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_all.ps1
```

Testing

```powershell
pytest -q
```

This includes API integration tests for `/status` and `/upload` using Flask's test client.

Environment variables

- Backend:
	- `CORS_ORIGINS` (comma-separated allowlist, example: `https://your-frontend.vercel.app`)
	- `MAX_UPLOAD_MB` (default: `25`)
	- `PORT` (default: `8000`)
	- `FLASK_DEBUG` (`true`/`false`, default: `false`)
- Frontend:
	- `VITE_API_BASE_URL` (example: `https://your-backend.onrender.com`)

Create local frontend env file:

```powershell
copy frontend/.env.example frontend/.env
```

Deployment (recommended)

1. Deploy backend (Render/Railway):
	 - Build command: `pip install -r requirements.txt`
	 - Start command: `gunicorn src.wsgi:app`
	 - Set env vars: `CORS_ORIGINS`, `MAX_UPLOAD_MB`
	- Optional: use `render.yaml` for one-click Render setup.

2. Deploy frontend (Vercel/Netlify):
	 - Build command: `npm run build`
	 - Output directory: `dist`
	 - Set env var: `VITE_API_BASE_URL=https://<your-backend-domain>`
	- Vercel config is included in `frontend/vercel.json`.
	- Netlify config is included in `frontend/netlify.toml`.

3. After deploy, set backend `CORS_ORIGINS` to the exact frontend domain.

Quick deploy checklist

1. Push latest code to GitHub.
2. Create Render service from this repository (or use `render.yaml`).
3. Deploy frontend from the `frontend` folder in Vercel (or Netlify).
4. Set `VITE_API_BASE_URL` to your Render backend URL.
5. Update backend `CORS_ORIGINS` with your deployed frontend URL.

Outputs

- `output/redacted.docx` — redacted document
- `output/mapping.json` — mapping from original → fake (persists between runs)
- `reports/evaluation_report.md` — formatted evaluation when `--ground_truth` provided

Project layout

```
scalerai/
├─ src/                # source modules (detectors, extractor, writer, anonymizer, evaluator)
├─ input/              # input DOCX files (put prospectus here)
├─ output/             # redacted.docx and mapping.json
├─ reports/            # evaluation report
├─ tests/              # ground-truth examples for evaluation
├─ requirements.txt
└─ README.md
```

Next improvements you can request

- Expand ground-truth and run evaluation on a real prospectus for reliable metrics.
- Add more conservative company/address heuristics or a small gazetteer of cities/terms to reduce false positives.
- Integrate Microsoft Presidio for production-grade PII detection.
- Add unit tests and CI integration.

