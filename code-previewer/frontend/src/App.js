import React, { useState } from 'react';
import axios from 'axios';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const LANGUAGE_MAP = {
  js: 'javascript',
  jsx: 'jsx',
  ts: 'typescript',
  tsx: 'tsx',
  py: 'python',
  java: 'java',
  cpp: 'cpp',
  c: 'c',
  txt: 'text',
};

function getLanguage(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  return LANGUAGE_MAP[ext] || 'text';
}

function App() {
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setError('');
    setLoading(true);

    const formData = new FormData();
    formData.append('codefile', file);

    try {
      const res = await axios.post('http://localhost:4000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setCode(res.data.content);
      setFilename(res.data.filename);
    } catch (err) {
      setError('Failed to upload file. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Code Previewer</h1>
        <p style={styles.subtitle}>Upload a code file to view it with syntax highlighting</p>
      </header>

      <div style={styles.uploadBox}>
        <label style={styles.uploadLabel}>
          <input
            type="file"
            accept=".js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.txt"
            onChange={handleFileUpload}
            style={styles.fileInput}
          />
          Choose a file
        </label>
      </div>

      {loading && <p style={styles.loading}>Loading…</p>}
      {error && <p style={styles.error}>{error}</p>}

      {code && (
        <div style={styles.codeBox}>
          <div style={styles.filenameBar}>
            <span style={styles.filename}>{filename}</span>
          </div>
          <SyntaxHighlighter
            language={getLanguage(filename)}
            style={atomDark}
            showLineNumbers
            customStyle={styles.highlighter}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#1a1a2e',
    color: '#e0e0e0',
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    padding: '2rem',
  },
  header: {
    textAlign: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2.5rem',
    color: '#00d4ff',
    margin: 0,
  },
  subtitle: {
    color: '#a0a0b0',
    marginTop: '0.5rem',
  },
  uploadBox: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '1.5rem',
  },
  uploadLabel: {
    display: 'inline-block',
    padding: '0.75rem 2rem',
    backgroundColor: '#00d4ff',
    color: '#1a1a2e',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: '1rem',
  },
  fileInput: {
    display: 'none',
  },
  loading: {
    textAlign: 'center',
    color: '#a0a0b0',
  },
  error: {
    textAlign: 'center',
    color: '#ff6b6b',
  },
  codeBox: {
    borderRadius: '8px',
    overflow: 'hidden',
    maxWidth: '900px',
    margin: '0 auto',
    boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
  },
  filenameBar: {
    backgroundColor: '#16213e',
    padding: '0.5rem 1rem',
    borderBottom: '1px solid #333',
  },
  filename: {
    color: '#00d4ff',
    fontWeight: 'bold',
    fontSize: '0.9rem',
  },
  highlighter: {
    margin: 0,
    borderRadius: 0,
    fontSize: '0.9rem',
  },
};

export default App;
