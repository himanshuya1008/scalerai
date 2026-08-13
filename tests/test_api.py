from io import BytesIO

from docx import Document

from src.api import app


def _build_docx_bytes() -> bytes:
    doc = Document()
    doc.add_paragraph("John Doe lives in Bangalore and email is john@example.com")
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def test_status_endpoint():
    client = app.test_client()
    response = client.get('/status')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['status'] == 'ok'
    assert payload['max_upload_mb'] >= 1


def test_upload_endpoint_returns_docx():
    client = app.test_client()
    payload = _build_docx_bytes()

    response = client.post(
        '/upload',
        data={
            'file': (BytesIO(payload), 'sample.docx'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    content_type = response.headers.get('Content-Type', '')
    assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type
    assert len(response.data) > 0
