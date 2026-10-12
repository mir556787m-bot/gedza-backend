// frontend/src/api/index.js
import axios from 'axios';

// ─── Мок-реализации ───
import {
  cartGetMock,
  cartChangeMock,
  cartRemoveMock,
  cartClearMock,
  cartCommentMock,
  cartPaymentMock,
  cartDatetimeMock,
  cartPromoAddMock,
  cartPromoDeleteMock,
  cartAdditionMock,
  cartAvailablePromosMock,
  cartCreateOrderMock,
  cartStopListMock,
  cartTogglePromoMock,
} from './mock/cartMock';

import {
  getOrderStatusMock,
  getOrderHistoryMock,
  reorderMock,
} from './mock/ordersMock';

import { menuMock } from './mock/menuMock';

import {
  getUserProfileMock,
  registerUserMock,
  addAddressMock,
  getAddressesMock,
  deleteAddressMock,
  initSessionMock,
  getSessionMock,
  getRestaurantsMock,
  wheelStatusMock,
  wheelSpinMock,
} from './mock/userMock';

import { getDb, updateDb } from './mock/mockStorage';

// ─── JWT (auth.js) ───
import {
  getAccessToken,
  refreshAccessToken,
  clearTokens,
} from './auth';

// ─── Флаг: используем мок или реальный API ───
const USE_MOCK_RAW = import.meta.env.VITE_USE_MOCK;

const _isProductionDomain = () => {
  const origin = window.location.origin || '';
  return (
    origin.includes('gedza') ||
    origin.includes('217.60.186.161') ||
    origin.includes('nip.io')
  );
};

const USE_MOCK =
  USE_MOCK_RAW === 'true' ||
  (USE_MOCK_RAW === 'auto' && !_isProductionDomain()) ||
  (USE_MOCK_RAW === undefined && !_isProductionDomain());

if (USE_MOCK) {
  console.log('[api] Режим: MOCK (localStorage)');
} else {
  console.log('[api] Режим: REAL API (JWT)');
}

// ─── Реальный клиент ───
const API_BASE_URL = window.location.origin;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ⚡ REQUEST interceptor — добавляет JWT
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  // Совместимость: MAX initData (для /api/v1/auth)
  if (window.WebApp?.initData) {
    config.headers['X-Max-Init-Data'] = window.WebApp.initData;
  }
  return config;
});

// ⚡ RESPONSE interceptor — авто-refresh при 401
let isRefreshing = false;
let refreshQueue = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({ resolve, reject });
        }).then((token) => {
          original.headers['Authorization'] = `Bearer ${token}`;
          return api(original);
        });
      }

      isRefreshing = true;
      try {
        const { access_token } = await refreshAccessToken();
        refreshQueue.forEach(({ resolve }) => resolve(access_token));
        refreshQueue = [];
        original.headers['Authorization'] = `Bearer ${access_token}`;
        return api(original);
      } catch (e) {
        refreshQueue.forEach(({ reject }) => reject(e));
        refreshQueue = [];
        clearTokens();
        window.dispatchEvent(new Event('auth:expired'));
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ─── Имитация задержки сети для мока ───
const delay = (ms = 200) => new Promise((r) => setTimeout(r, ms));

async function mockWrapper(fn, ...args) {
  await delay(150 + Math.random() * 200);
  return fn(...args);
}

// ═══════════════════════════════════════════════════════════
//  МЕНЮ
// ═══════════════════════════════════════════════════════════

export const fetchMenu = async () => {
  if (USE_MOCK) return mockWrapper(menuMock);
  const r = await api.get('/api/menu', {
    validateStatus: (status) =>
      (status >= 200 && status < 300) || status === 202,
  });
  if (r.status === 202) return [];
  return r.data?.items || [];
};

// ═══════════════════════════════════════════════════════════
//  СЕССИЯ
// ═══════════════════════════════════════════════════════════

export const getSession = async (userId) => {
  if (USE_MOCK) {
    const res = await mockWrapper(getSessionMock, userId);
    return res.session;
  }
  const r = await api.get('/api/v1/session/me');   // ⚡ без user_id
  return r.data.session;
};

export const initSession = async (userId, deliveryType, address, addressDetails = null) => {
  if (USE_MOCK) {
    const res = await mockWrapper(
      initSessionMock,
      userId,
      deliveryType,
      address,
      addressDetails
    );
    return res.session;
  }
  const r = await api.post('/api/v1/session/init', {
    delivery_type: deliveryType,
    address,
    address_details: addressDetails,
  });
  return r.data.session;
};

export const sessionInit = initSession;

// ═══════════════════════════════════════════════════════════
//  АДРЕСА
// ═══════════════════════════════════════════════════════════

export const getAddresses = async (userId) => {
  if (USE_MOCK) return mockWrapper(getAddressesMock, userId);
  const r = await api.get('/api/v1/user/addresses');
  return r.data;
};

export const addAddress = async (userId, address, addressDetails = null, isDefault = false) => {
  if (USE_MOCK) {
    return mockWrapper(addAddressMock, userId, address, addressDetails, isDefault);
  }
  const r = await api.post('/api/v1/user/addresses', {
    address,
    address_details: addressDetails,
    is_default: isDefault,
  });
  return r.data;
};

export const deleteAddress = async (userId, addressId) => {
  if (USE_MOCK) return mockWrapper(deleteAddressMock, userId, addressId);
  const r = await api.delete(`/api/v1/user/addresses/${addressId}`);
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  РЕСТОРАНЫ
// ═══════════════════════════════════════════════════════════

export const getRestaurants = async (lat = null, lon = null) => {
  if (USE_MOCK) return mockWrapper(getRestaurantsMock);
  const params = new URLSearchParams();
  if (lat) params.append('lat', lat);
  if (lon) params.append('lon', lon);
  const r = await api.get(`/api/v1/restaurants/list?${params}`);
  return r.data.restaurants;
};

// ═══════════════════════════════════════════════════════════
//  ОПЛАТА
// ═══════════════════════════════════════════════════════════

export const setPayment = async (userId, paymentType) => {
  if (USE_MOCK) return mockWrapper(cartPaymentMock, userId, paymentType);
  const r = await api.post('/api/v1/payment/set', {
    payment_type: paymentType,
  });
  return r.data;
};

export const getPayment = async (userId) => {
  if (USE_MOCK) return { payment_type: null };
  const r = await api.get('/api/v1/payment/get');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  ПРЕДЗАКАЗ
// ═══════════════════════════════════════════════════════════

export const setOrderTime = async (userId, orderTime) => {
  if (USE_MOCK) return mockWrapper(cartDatetimeMock, userId, orderTime);
  const r = await api.post('/api/v1/order-time/set', {
    order_time: orderTime,
  });
  return r.data;
};

export const getOrderTime = async (userId) => {
  if (USE_MOCK) return { order_time: 'now' };
  const r = await api.get('/api/v1/order-time/get');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  КОЛЕСО ФОРТУНЫ
// ═══════════════════════════════════════════════════════════

export const wheelStatus = async (userId) => {
  if (USE_MOCK) return mockWrapper(wheelStatusMock, userId);
  const r = await api.get('/api/v1/wheel/status');
  return r.data;
};

export const wheelSpin = async (userId) => {
  if (USE_MOCK) return mockWrapper(wheelSpinMock, userId);
  const r = await api.post('/api/v1/wheel/spin');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  ПРОМОКОДЫ (устаревший)
// ═══════════════════════════════════════════════════════════

export const applyPromo = async (userId, code, cartTotal) => {
  if (USE_MOCK) return mockWrapper(cartPromoAddMock, userId, code);
  const r = await api.post('/api/v1/promocodes/apply', {
    code,
    cart_total: cartTotal,
  });
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  КОРЗИНА
// ═══════════════════════════════════════════════════════════

export const cartGet = async (userId) => {
  if (USE_MOCK) return mockWrapper(cartGetMock, userId);
  const r = await api.get('/api/v1/cart/get');
  return r.data;
};

export const cartChange = async (userId, plateId, count) => {
  if (USE_MOCK) return mockWrapper(cartChangeMock, userId, plateId, count);
  const r = await api.post(
    `/api/v1/cart/change?plate_id=${plateId}&count=${count}`
  );
  return r.data;
};

export const cartRemove = async (userId, plateId) => {
  if (USE_MOCK) return mockWrapper(cartRemoveMock, userId, plateId);
  const r = await api.post(
    `/api/v1/cart/remove?plate_id=${plateId}`
  );
  return r.data;
};

export const cartClear = async (userId) => {
  if (USE_MOCK) return mockWrapper(cartClearMock, userId);
  const r = await api.post('/api/v1/cart/clear');
  return r.data;
};

export const cartComment = async (userId, comment) => {
  if (USE_MOCK) return mockWrapper(cartCommentMock, userId, comment);
  const r = await api.post(
    `/api/v1/cart/comment?comment=${encodeURIComponent(comment)}`
  );
  return r.data;
};

export const cartPayment = async (userId, paymentType) => {
  if (USE_MOCK) return mockWrapper(cartPaymentMock, userId, paymentType);
  const r = await api.post(
    `/api/v1/cart/payment?payment_type=${paymentType}`
  );
  return r.data;
};

export const cartDatetime = async (userId, datetime) => {
  if (USE_MOCK) return mockWrapper(cartDatetimeMock, userId, datetime);
  const r = await api.post(
    `/api/v1/cart/datetime?order_datetime=${encodeURIComponent(datetime)}`
  );
  return r.data;
};

export const cartPromoAdd = async (userId, code) => {
  if (USE_MOCK) return mockWrapper(cartPromoAddMock, userId, code);
  const r = await api.post(
    `/api/v1/cart/promo/add?code=${encodeURIComponent(code)}`
  );
  return r.data;
};

export const cartPromoDelete = async (userId) => {
  if (USE_MOCK) return mockWrapper(cartPromoDeleteMock, userId);
  const r = await api.post('/api/v1/cart/promo/delete');
  return r.data;
};

export const cartAddition = async (userId, additionId, delta) => {
  if (USE_MOCK) return mockWrapper(cartAdditionMock, userId, additionId, delta);
  const r = await api.post(
    `/api/v1/cart/addition?addition_id=${additionId}&delta=${delta}`
  );
  return r.data;
};

export const cartAvailablePromos = async (userId) => {
  if (USE_MOCK) return mockWrapper(cartAvailablePromosMock, userId);
  const r = await api.get('/api/v1/cart/promo/available');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  ОФОРМЛЕНИЕ ЗАКАЗА
// ═══════════════════════════════════════════════════════════

export const cartCreateOrder = async (userId, phone, address = null, marketingConsent = true) => {
  if (USE_MOCK) {
    return mockWrapper(cartCreateOrderMock, userId, phone, address, marketingConsent);
  }
  const params = new URLSearchParams({
    phone,
    marketing_consent: marketingConsent,
  });
  if (address) params.append('address', address);
  const r = await api.post(`/api/v1/cart/create-order?${params}`);
  return r.data;
};

export const cartPhone = async (userId, phone) => {
  if (USE_MOCK) return { success: true };
  const r = await api.post(
    `/api/v1/cart/phone?phone=${encodeURIComponent(phone)}`
  );
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  СТОП-ЛИСТ
// ═══════════════════════════════════════════════════════════

export const cartStopList = async (userId) => {
  if (USE_MOCK) return mockWrapper(cartStopListMock, userId);
  const r = await api.get('/api/v1/cart/stoplist');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  ИСТОРИЯ И СТАТУС ЗАКАЗОВ
// ═══════════════════════════════════════════════════════════

export const getOrderStatus = async (orderId) => {
  if (USE_MOCK) return mockWrapper(getOrderStatusMock, orderId);
  const r = await api.get(`/api/v1/order/status?order_id=${orderId}`);
  return r.data;
};

export const getOrderHistory = async (userId) => {
  if (USE_MOCK) return mockWrapper(getOrderHistoryMock, userId);
  const r = await api.get('/api/v1/order/history');
  return r.data;
};

export const reorder = async (userId, orderId) => {
  if (USE_MOCK) return mockWrapper(reorderMock, userId, orderId);
  const r = await api.post(
    `/api/v1/order/reorder?order_id=${orderId}`
  );
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  РЕГИСТРАЦИЯ / ПРОФИЛЬ
// ═══════════════════════════════════════════════════════════

export const registerUser = async (
  userId,
  phone,
  address,
  legalAgreed = true,
  name = '',
  addressDetails = null
) => {
  if (USE_MOCK) {
    return mockWrapper(
      registerUserMock,
      userId,
      phone,
      address,
      legalAgreed,
      name,
      addressDetails
    );
  }
  const r = await api.post('/api/v1/user/register', {
    name,
    phone,
    address,
    address_details: addressDetails,
    legal_agreed: legalAgreed,
  });
  return r.data;
};

export const getUserProfile = async (userId) => {
  if (USE_MOCK) return mockWrapper(getUserProfileMock, userId);
  const r = await api.get('/api/v1/user/profile');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  КОМАНДЫ ПРОМОКОДОВ (аналог SellKit)
// ═══════════════════════════════════════════════════════════

export const cartSetPromos = async (userId, promosIdsString) => {
  if (USE_MOCK) {
    const db = getDb();
    db.cart.promosIdsString = promosIdsString;
    updateDb({ cart: db.cart });
    return { success: true, promosIdsString };
  }
  const r = await api.post('/api/v1/cart/command/set-promos', {
    promosIdsString,
  });
  return r.data;
};

export const cartTogglePromo = async (userId, promoId) => {
  if (USE_MOCK) {
    return mockWrapper(cartTogglePromoMock, userId, promoId);
  }
  const r = await api.post(
    `/api/v1/cart/command/toggle-promo?promo_id=${promoId}`
  );
  return r.data;
};

export const cartClearPromos = async (userId) => {
  if (USE_MOCK) {
    const db = getDb();
    db.cart.promosIdsString = '';
    db.cart.promoCode = null;
    updateDb({ cart: db.cart });
    return { success: true, promosIdsString: '' };
  }
  const r = await api.post('/api/v1/cart/command/clear-promos');
  return r.data;
};

// ═══════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════

export { loginWithInitData } from './auth';