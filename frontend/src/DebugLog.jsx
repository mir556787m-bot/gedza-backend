import { useEffect, useState } from 'react';

export default function DebugLog() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const originalLog = console.log;
    const originalWarn = console.warn;
    const originalError = console.error;

    const addLog = (type, args) => {
      const text = args
        .map((a) => {
          if (typeof a === 'string') return a;
          if (typeof a === 'object') {
            try { return JSON.stringify(a).slice(0, 100); }
            catch { return String(a); }
          }
          return String(a);
        })
        .join(' ')
        .slice(0, 200);

      setLogs((prev) => [...prev.slice(-30), `[${type}] ${text}`]);
    };

    console.log = (...args) => { addLog('LOG', args); originalLog(...args); };
    console.warn = (...args) => { addLog('WARN', args); originalWarn(...args); };
    console.error = (...args) => { addLog('ERR', args); originalError(...args); };

    return () => {
      console.log = originalLog;
      console.warn = originalWarn;
      console.error = originalError;
    };
  }, []);

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      maxHeight: '40vh',
      background: 'rgba(0,0,0,0.85)',
      color: '#0f0',
      fontSize: '10px',
      fontFamily: 'monospace',
      padding: '6px',
      overflowY: 'auto',
      zIndex: 999999,
      pointerEvents: 'auto',
    }}>
      <div style={{ color: '#ff0', marginBottom: '4px', fontWeight: 'bold' }}>
        DEBUG LOG ({logs.length})
      </div>
      {logs.map((l, i) => (
        <div key={i} style={{ wordBreak: 'break-all', marginBottom: '2px' }}>{l}</div>
      ))}
    </div>
  );
}