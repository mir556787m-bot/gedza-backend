// frontend/src/hooks/useOrderTracking.js
import { useEffect, useRef, useState, useCallback } from 'react';
import { getAccessToken } from '../api/auth';

export function useOrderTracking() {
  const [status, setStatus] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const pingRef = useRef(null);
  const reconnectRef = useRef(null);
  const attemptRef = useRef(0);

  const connect = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/v1/ws/track-order?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      attemptRef.current = 0;

      // Пинг каждые 30 сек
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'status_changed') {
          setStatus(data);
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (pingRef.current) clearInterval(pingRef.current);

      // Exponential backoff: 1s, 2s, 4s, 8s... до 30s
      const delay = Math.min(30000, 1000 * Math.pow(2, attemptRef.current));
      attemptRef.current += 1;
      reconnectRef.current = setTimeout(connect, delay);
    };

    ws.onerror = (e) => {
      console.warn('WS error:', e);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pingRef.current) clearInterval(pingRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connect]);

  return { status, connected };
}