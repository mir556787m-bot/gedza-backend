// frontend/src/api.js
import axios from 'axios';

const API_BASE_URL = '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchMenu = async () => {
  const response = await api.get('/api/menu');
  return response.data.items;
};

export const updateCart = async (userId, itemId, quantity) => {
  const response = await api.post('/api/cart/update', {
    user_id: userId,
    item_id: itemId,
    quantity: quantity,
  });
  return response.data;
};

export const fetchCart = async (userId) => {
  const response = await api.get(`/api/cart/${userId}`);
  return response.data.cart;
};

export const clearCart = async (userId) => {
  const response = await api.delete(`/api/cart/${userId}`);
  return response.data;
};

export const createOrder = async (userId, address, phone, comment = "") => {
  const response = await api.post('/api/order', {
    user_id: userId,
    address: address,
    phone: phone,
    comment: comment,
    payment_method: "sbp",
  });
  return response.data;
};