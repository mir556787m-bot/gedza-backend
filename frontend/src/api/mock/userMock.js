// frontend/src/api/mock/userMock.js
import { getDb, updateDb } from './mockStorage';

export async function getUserProfileMock(userId) {
  const db = getDb();
  return { profile: db.user };
}

export async function registerUserMock(userId, phone, address, legalAgreed, name, addressDetails) {
  const db = getDb();
  db.user = {
    ...db.user,
    name,
    phone,
    address,
    addressDetails,
    legal_agreed: legalAgreed,
  };
  updateDb({ user: db.user });
  return { profile: db.user };
}

export async function addAddressMock(userId, address, addressDetails, isDefault) {
  const db = getDb();
  const newAddr = {
    id: Date.now(),
    address,
    address_details: addressDetails,
    is_default: isDefault,
  };
  db.addresses = [...(db.addresses || []), newAddr];
  updateDb({ addresses: db.addresses });
  return newAddr;
}

export async function getAddressesMock(userId) {
  const db = getDb();
  return { addresses: db.addresses || [] };
}

export async function deleteAddressMock(userId, addressId) {
  const db = getDb();
  db.addresses = (db.addresses || []).filter((a) => a.id !== addressId);
  updateDb({ addresses: db.addresses });
  return { success: true };
}

export async function initSessionMock(userId, deliveryType, address, addressDetails) {
  const db = getDb();
  db.session = {
    deliveryType,
    address,
    addressFull: addressDetails
      ? `${address}, кв ${addressDetails.flat || '-'}, этаж ${addressDetails.floor || '-'}, подъезд ${addressDetails.entrance || '-'}`
      : address,
  };
  updateDb({ session: db.session });
  return { session: db.session };
}

export async function getSessionMock(userId) {
  const db = getDb();
  return { session: db.session };
}

export async function getRestaurantsMock() {
  return [
    {
      id: 1,
      name: 'Gedza Черниковка',
      address: 'г. Уфа, ул. Первомайская, 12',
      schedule: 'Пн-Вс 10:00–22:30',
      phone: '+7 (347) 200 30 04',
      delivery_minutes: 90,
    },
    {
      id: 2,
      name: 'Gedza Сипайлово',
      address: 'г. Уфа, ул. Маршала Жукова, 5',
      schedule: 'Пн-Вс 10:00–22:30',
      phone: '+7 (347) 200 30 05',
      delivery_minutes: 60,
    },
  ];
}

export async function wheelStatusMock(userId) {
  return { canSpin: true };
}

export async function wheelSpinMock(userId) {
  const prizes = ['Суши Пончик', 'Онигири', 'Удон с курицей', 'Суши торт', 'Фортуна сет'];
  const prize = prizes[Math.floor(Math.random() * prizes.length)];
  return { angle: Math.floor(Math.random() * 360) + 720, prize_name: prize };
}