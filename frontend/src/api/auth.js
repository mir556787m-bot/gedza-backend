// frontend/src/api/auth.js
import axios from 'axios';

const API_BASE_URL = window.location.origin;

let accessToken = null;   // ⚡ Только в памяти! Не в localStorage.
let refreshToken = null;

export function getAccessToken() {
  return accessToken;
}

export function setTokens({ access_token, refresh_token }) {
  accessToken = access_token;
  refreshToken = refresh_token;
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
}

export async function loginWithInitData() {
  const initData = window.WebApp?.initData;
  if (!initData) {
    throw new Error('No initData from MAX Bridge');
  }

  const r = await axios.post(`${API_BASE_URL}/api/v1/auth`, {
    init_data: initData,
  });

  setTokens({
    access_token: r.data.access_token,
    refresh_token: r.data.refresh_token,
  });

  return r.data;
}

export async function refreshAccessToken() {
  if (!refreshToken) throw new Error('No refresh token');
  const r = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
    refresh_token: refreshToken,
  });
  setTokens({
    access_token: r.data.access_token,
    refresh_token: r.data.refresh_token,
  });
  return r.data;
}

