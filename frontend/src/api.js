// frontend/src/api.js
import axios from 'axios';

// Используем текущий origin (localhost или Tuna-URL — не важно)
const API_BASE_URL = window.location.origin;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Автоматически добавляем initData от MAX Bridge в каждый запрос
api.interceptors.request.use((config) => {
  if (window.WebApp?.initData) {
    config.headers['X-Max-Init-Data'] = window.WebApp.initData;
  }
  return config;
});

// === Меню ===
export const fetchMenu = async () => {
  const response = await api.get('/api/menu');
  return response.data.items;
};

// === Корзина ===
export const fetchCart = async (userId) => {
  const response = await api.get(`/api/cart/${userId}`);
  return response.data.cart;
};

export const updateCart = async (userId, itemId, quantity) => {
  const response = await api.post('/api/cart/update', {
    user_id: userId,
    item_id: itemId,
    quantity: quantity,
  });
  return response.data;
};

export const clearCart = async (userId) => {
  const response = await api.delete(`/api/cart/${userId}`);
  return response.data;
};

// === Заказ ===
export const createOrder = async (userId, address, phone, comment = '') => {
  const response = await api.post('/api/order', {
    user_id: userId,
    address: address,
    phone: phone,
    comment: comment,
    payment_method: 'sbp',
  });
  return response.data;
};

// === MAX Bot API (для отправки уведомлений) ===
export const notifyMaxBot = async (userId, message) => {
  const response = await api.post('/api/notify', {
    user_id: userId,
    message: message,
  });
  return response.data;
};