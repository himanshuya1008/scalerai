import { useState } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setStatus('Please choose a DOCX file.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    setStatus('Uploading and redacting...');
    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Upload failed.');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `redacted_${file.name}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus('Redacted document downloaded successfully.');
    } catch (error) {
      setStatus(error.message || 'Upload failed.');
    }
  };

  return (
    <div style={{
      maxWidth: 640,
      margin: '48px auto',
      padding: 24,
      fontFamily: 'Arial, sans-serif',
      border: '1px solid #e5e7eb',
      borderRadius: 12,
      background: '#f9fafb'
    }}>
      <h2 style={{ marginBottom: 16 }}>PII Redaction Tool</h2>
      <p style={{ color: '#374151', marginBottom: 20 }}>
        Upload a DOCX file to redact names, emails, phones, addresses, SSNs, card numbers, dates, and IPs.
      </p>
      <form onSubmit={handleSubmit}>
        <input type="file" accept=".docx" onChange={(e) => setFile(e.target.files[0])} />
        <div style={{ marginTop: 20 }}>
          <button type="submit" style={{ padding: '10px 18px', cursor: 'pointer' }}>
            Redact DOCX
          </button>
        </div>
      </form>
      <p style={{ marginTop: 20, color: '#111827', fontWeight: 600 }}>{status}</p>
    </div>
  );
}

export default App;