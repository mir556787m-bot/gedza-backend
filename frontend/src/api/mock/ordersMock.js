// frontend/src/api/mock/ordersMock.js
import { getDb, saveDb } from './mockStorage';

export async function getOrderStatusMock(orderId) {
  const db = getDb();
  const order = db.orders.find((o) => o.id === orderId);
  if (!order) throw new Error('Заказ не найден');

  const created = new Date(order.createdAt).getTime();
  const elapsed = Date.now() - created;
  const MINUTE = 60 * 1000;

  if (order.status === 'pending' && elapsed > 1 * MINUTE) {
    order.status = 'confirmed';
    order.statusText = 'ПОДТВЕРЖДЁН';
  } else if (order.status === 'confirmed' && elapsed > 3 * MINUTE) {
    order.status = 'cooking';
    order.statusText = 'ГОТОВИТСЯ';
  } else if (order.status === 'cooking' && elapsed > 10 * MINUTE) {
    order.status = 'delivering';
    order.statusText = 'В ДОСТАВКЕ';
  } else if (order.status === 'delivering' && elapsed > 30 * MINUTE) {
    order.status = 'delivered';
    order.statusText = 'ДОСТАВЛЕН';
  }

  saveDb();
  return { order };
}

export async function getOrderHistoryMock(userId) {
  const db = getDb();
  return { orders: db.orders };
}

export async function reorderMock(userId, orderId) {
  const db = getDb();
  const order = db.orders.find((o) => o.id === orderId);
  if (!order) throw new Error('Заказ не найден');

  db.cart.plates = order.items.map((item) => ({
    plateID: item.id,
    plateName: item.name,
    thumbnailPicture: item.image,
    mass: item.mass,
    count: item.count,
    price: item.price,
  }));
  db.cart.additions = [];
  db.cart.promoCode = null;
  saveDb();

  return { success: true };
}