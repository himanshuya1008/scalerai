import { useState, useEffect } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

// Dynamically inject Outfit font for premium typography
if (!document.getElementById('outfit-font-link')) {
  const link = document.createElement('link');
  link.id = 'outfit-font-link';
  link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap';
  link.rel = 'stylesheet';
  document.head.appendChild(link);
}

function App() {
  const [file, setFile] = useState(null);
  const [gtFile, setGtFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, processing, success, error
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setErrorMsg('Please select a DOCX file to redact.');
      setStatus('error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (gtFile) {
      formData.append('ground_truth', gtFile);
    }

    setStatus('processing');
    setErrorMsg('');

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let parsedError = 'Upload and redaction failed.';
        try {
          const errObj = JSON.parse(errorText);
          parsedError = errObj.error || parsedError;
        } catch {
          parsedError = errorText || parsedError;
        }
        throw new Error(parsedError);
      }

      // Read custom headers from response
      const detected = response.headers.get('X-Entities-Detected') || '0';
      const redacted = response.headers.get('X-Entities-Redacted') || '0';
      const breakdown = JSON.parse(response.headers.get('X-Category-Breakdown') || '{}');
      const hasEvaluation = response.headers.get('X-Has-Evaluation') === 'true';
      const precision = response.headers.get('X-Precision') || '0.000';
      const recall = response.headers.get('X-Recall') || '0.000';
      const f1 = response.headers.get('X-F1') || '0.000';
      const accuracy = response.headers.get('X-Accuracy') || '0.000';
      const mappingCount = response.headers.get('X-Mapping-Count') || '0';
      const processingTime = response.headers.get('X-Processing-Time') || '0.000s';

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);

      setResult({
        detected,
        redacted,
        breakdown,
        hasEvaluation,
        precision,
        recall,
        f1,
        accuracy,
        mappingCount,
        processingTime,
        downloadUrl,
        fileName: `redacted_${file.name}`
      });
      setStatus('success');
    } catch (error) {
      setErrorMsg(error instanceof Error ? error.message : 'Server communication failed.');
      setStatus('error');
    }
  };

  const handleReset = () => {
    setFile(null);
    setGtFile(null);
    setStatus('idle');
    setErrorMsg('');
    if (result?.downloadUrl) {
      window.URL.revokeObjectURL(result.downloadUrl);
    }
    setResult(null);
  };

  const handleDownload = () => {
    if (!result) return;
    const link = document.createElement('a');
    link.href = result.downloadUrl;
    link.download = result.fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(ellipse at bottom, #1b2735 0%, #090a0f 100%)',
      color: '#f3f4f6',
      fontFamily: '"Outfit", sans-serif',
      padding: '40px 20px',
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes float {
          0% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
          100% { transform: translateY(0px); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        .glass-panel {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 20px;
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .btn-primary {
          background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
          border: none;
          color: white;
          padding: 12px 24px;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }
        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        }
        .btn-secondary {
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          color: #f3f4f6;
          padding: 12px 24px;
          border-radius: 10px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        .btn-secondary:hover {
          background: rgba(255, 255, 255, 0.2);
        }
        .form-label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: #d1d5db;
        }
        .file-zone {
          border: 2px dashed rgba(255, 255, 255, 0.2);
          border-radius: 12px;
          padding: 30px;
          text-align: center;
          background: rgba(255, 255, 255, 0.02);
          transition: all 0.3s ease;
          cursor: pointer;
          position: relative;
        }
        .file-zone:hover {
          border-color: #818cf8;
          background: rgba(99, 102, 241, 0.05);
        }
      `}</style>

      <div className="glass-panel" style={{
        maxWidth: 720,
        width: '100%',
        padding: 40,
        boxSizing: 'border-box'
      }}>
        {/* Title */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{
            fontSize: '2.5rem',
            margin: '0 0 10px 0',
            fontWeight: 700,
            background: 'linear-gradient(135deg, #a5b4fc 0%, #e9d5ff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.025em'
          }}>
            PII Redaction Tool
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '1rem', margin: 0 }}>
            Redact names, emails, phones, SSNs, credit cards, IPs, addresses, and DOBs inside DOCX documents.
          </p>
        </div>

        {/* View States */}
        {status === 'idle' && (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div>
              <label className="form-label">Upload DOCX File (Required)</label>
              <div className="file-zone" onClick={() => document.getElementById('docx-input').click()}>
                <input
                  id="docx-input"
                  type="file"
                  accept=".docx"
                  style={{ display: 'none' }}
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <span style={{ fontSize: '1.2rem', color: file ? '#a5b4fc' : '#9ca3af', fontWeight: 500 }}>
                  {file ? `📄 ${file.name}` : '📁 Drag & drop or click to choose DOCX file'}
                </span>
                {file && (
                  <p style={{ fontSize: '0.85rem', color: '#9ca3af', margin: '8px 0 0 0' }}>
                    Size: {(file.size / 1024).toFixed(1)} KB
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="form-label">Upload Ground Truth JSON (Optional - for Evaluation)</label>
              <div className="file-zone" onClick={() => document.getElementById('gt-input').click()} style={{ padding: 20 }}>
                <input
                  id="gt-input"
                  type="file"
                  accept=".json"
                  style={{ display: 'none' }}
                  onChange={(e) => setGtFile(e.target.files?.[0] || null)}
                />
                <span style={{ fontSize: '1rem', color: gtFile ? '#c084fc' : '#9ca3af' }}>
                  {gtFile ? `📊 Ground Truth: ${gtFile.name}` : '⚙️ Click to choose ground_truth.json'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12 }}>
              <button type="submit" className="btn-primary" style={{ width: '100%', fontSize: '1.1rem' }}>
                Redact DOCX
              </button>
            </div>
          </form>
        )}

        {status === 'processing' && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <div className="animate-spin" style={{
              width: 60,
              height: 60,
              border: '6px solid rgba(255, 255, 255, 0.1)',
              borderTopColor: '#818cf8',
              borderRadius: '50%',
              margin: '0 auto 24px auto'
            }} />
            <h3 style={{ fontSize: '1.4rem', marginBottom: 8, fontWeight: 600 }}>Processing File</h3>
            <p style={{ color: '#9ca3af', margin: 0 }}>Detecting PII elements, resolving overlaps, and rewriting DOCX runs...</p>
          </div>
        )}

        {status === 'success' && result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
            {/* Header message */}
            <div style={{
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: 12,
              padding: 20,
              textAlign: 'center'
            }}>
              <span style={{ fontSize: '2.5rem', display: 'block', marginBottom: 8 }}>✅</span>
              <h3 style={{ margin: '0 0 4px 0', fontSize: '1.3rem', color: '#34d399', fontWeight: 600 }}>
                Redaction Completed Successfully
              </h3>
              <p style={{ margin: 0, color: '#d1d5db', fontSize: '0.95rem' }}>
                Your redacted file is ready for download. Labels and formatting have been preserved.
              </p>
            </div>

            {/* Counts */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 20,
              textAlign: 'center'
            }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 20, borderRadius: 12, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ display: 'block', fontSize: '2.2rem', fontWeight: 700, color: '#818cf8' }}>
                  {result.detected}
                </span>
                <span style={{ fontSize: '0.85rem', color: '#9ca3af', textTransform: 'uppercase', tracking: '0.05em' }}>
                  PII Entities Detected
                </span>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 20, borderRadius: 12, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ display: 'block', fontSize: '2.2rem', fontWeight: 700, color: '#34d399' }}>
                  {result.redacted}
                </span>
                <span style={{ fontSize: '0.85rem', color: '#9ca3af', textTransform: 'uppercase', tracking: '0.05em' }}>
                  Entities Redacted
                </span>
              </div>
            </div>

            {/* Additional Metrics */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 16,
              textAlign: 'center',
              background: 'rgba(255, 255, 255, 0.02)',
              padding: 16,
              borderRadius: 12,
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <div>
                <span style={{ display: 'block', fontSize: '1.2rem', fontWeight: 600, color: '#e5e7eb' }}>
                  {result.processingTime}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase' }}>
                  Processing Time
                </span>
              </div>
              <div>
                <span style={{ display: 'block', fontSize: '1.2rem', fontWeight: 600, color: '#e5e7eb' }}>
                  {result.mappingCount}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase' }}>
                  Unique Mappings
                </span>
              </div>
              <div>
                <span style={{ display: 'block', fontSize: '1.2rem', fontWeight: 600, color: result.hasEvaluation ? '#fbbf24' : '#9ca3af' }}>
                  {result.hasEvaluation ? `${(parseFloat(result.f1) * 100).toFixed(1)}% F1` : 'N/A'}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase' }}>
                  Detection Success
                </span>
              </div>
            </div>

            {/* Category Breakdown */}
            <div>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '1.1rem', fontWeight: 600, color: '#e5e7eb' }}>
                PII Breakdown by Category
              </h4>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 10
              }}>
                {[
                  { key: 'PERSON', label: 'FULL NAME' },
                  { key: 'EMAIL', label: 'EMAIL' },
                  { key: 'PHONE', label: 'PHONE' },
                  { key: 'COMPANY', label: 'COMPANY' },
                  { key: 'ADDRESS', label: 'ADDRESS' },
                  { key: 'SSN', label: 'SSN' },
                  { key: 'CREDIT_CARD', label: 'CREDIT CARD' },
                  { key: 'DOB', label: 'DATE OF BIRTH' },
                  { key: 'IP_ADDRESS', label: 'IP ADDRESS' }
                ].map(({ key, label }) => {
                  const count = result.breakdown[key] || 0;
                  return (
                    <div key={key} style={{
                      background: count > 0 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                      border: count > 0 ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(255, 255, 255, 0.05)',
                      borderRadius: 20,
                      padding: '6px 14px',
                      fontSize: '0.9rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      opacity: count > 0 ? 1 : 0.5
                    }}>
                      <span style={{ fontWeight: 600, color: count > 0 ? '#a5b4fc' : '#9ca3af' }}>{label}</span>
                      <span style={{
                        background: count > 0 ? '#818cf8' : 'rgba(255, 255, 255, 0.1)',
                        color: count > 0 ? 'white' : '#9ca3af',
                        borderRadius: '50%',
                        width: 20,
                        height: 20,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.75rem',
                        fontWeight: 700
                      }}>{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Evaluation Stats (if available) */}
            {result.hasEvaluation && (
              <div style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: 16,
                padding: 24
              }}>
                <h4 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#c084fc', fontWeight: 600 }}>
                  Evaluation Metrics (vs Ground Truth)
                </h4>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: 16
                }}>
                  {[
                    { label: 'Precision', val: result.precision, color: '#34d399' },
                    { label: 'Recall', val: result.recall, color: '#60a5fa' },
                    { label: 'F1 Score', val: result.f1, color: '#fbbf24' },
                    { label: 'Accuracy', val: result.accuracy, color: '#f87171' }
                  ].map((m) => (
                    <div key={m.label} style={{ textAlign: 'center' }}>
                      <span style={{ display: 'block', fontSize: '1.6rem', fontWeight: 700, color: m.color }}>
                        {m.val}
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>{m.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div style={{
              display: 'flex',
              gap: 16,
              justifyContent: 'space-between',
              marginTop: 12
            }}>
              <button onClick={handleReset} className="btn-secondary" style={{ flex: 1 }}>
                Reset / Upload New File
              </button>
              <button onClick={handleDownload} className="btn-primary" style={{ flex: 1.5, fontSize: '1.05rem' }}>
                Download Redacted DOCX
              </button>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 12,
              padding: 20,
              textAlign: 'center'
            }}>
              <span style={{ fontSize: '2.5rem', display: 'block', marginBottom: 8 }}>❌</span>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '1.3rem', color: '#f87171', fontWeight: 600 }}>
                Redaction Failed
              </h3>
              <p style={{ margin: 0, color: '#fca5a5', fontSize: '0.95rem' }}>
                {errorMsg}
              </p>
            </div>

            <button onClick={handleReset} className="btn-secondary" style={{ width: '100%' }}>
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;