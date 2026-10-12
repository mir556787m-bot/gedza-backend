// frontend/src/api/mock/mockStorage.js

const STORAGE_KEY = 'gedza_mock_db';

const DEFAULT_DB = {
  user: {
    id: 12345,
    name: 'Иван',
    phone: '+7 (999) 123-45-67',
    address: 'Уфа, улица Юрия Гагарина, д. 50/2',
    addressDetails: {
      flat: '45',
      floor: '5',
      entrance: '2',
      door_code: '3',
      comment: 'Пр',
      is_private: false,
    },
    bonus: 0,
    legal_agreed: true,
  },
  session: {
    deliveryType: 'delivery',
    address: 'Уфа, улица Юрия Гагарина, д. 50/2',
    addressFull:
      'Уфа, улица Юрия Гагарина, д. 50/2, кв 45, этаж 5, подъезд 2, домофон 3',
  },
  cart: {
    plates: [],
    additions: [],
    usingPromocode: false,
    promoCode: null,
    // ⚡ Строка ID активных промокодов (эксклюзивно — только один)
    // Пример: "2" — только промокод с id=2 (СВОИ)
    // Пустая строка = промокоды не применены
    promosIdsString: '',
    orderDateTime: 'now',
    orderComment: '',
    lastOrderPaymentType: null,
  },
  orders: [],
  addresses: [],
  promos: [
    {
      id: 1,
      code: 'Самовывоз',
      title: 'Забери сам — 10% скидки',
      description: 'ЗАБЕРИ САМ — 10% СКИДКИ',
      tag: 'Самовывоз',
      type: 'pickup',
      delivery_types: '1',       // только для pickup
      discount: 0.10,
      percent: 10,
      auto_activate: true,
      is_hidden: false,
    },
    {
      id: 2,
      code: 'СВОИ',
      title: 'Суши торт в подарок к заказу от 890 ₽',
      description: 'Только для точек Черниковка/Сипайлово',
      tag: 'СВОИ',
      type: 'gift',
      delivery_types: '2',       // только для delivery
      minTotal: 890,
      giftPlateId: 999,
      giftName: 'Суши торт с курицей',
      giftImage:
        'https://placehold.co/200x200/d40000/ffffff?text=Sushi+Cake',
      auto_activate: false,
      is_hidden: false,
    },
    {
      id: 3,
      code: 'ВИТРИНА50',
      title: 'Витрина со скидкой 50%',
      description: 'Только для категории «Витрина»',
      tag: 'Витрина',
      type: 'category',
      delivery_types: '2',       // только для delivery
      category_name: 'Витрина- забери за 15 минут',
      applies_to_category_only: true,
      discount: 0.5,
      percent: 50,
      auto_activate: false,
      is_hidden: false,
    },
  ],
};

function loadDb() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return structuredClone(DEFAULT_DB);
    const saved = JSON.parse(raw);
    // Deep merge для новых полей
    return {
      ...structuredClone(DEFAULT_DB),
      ...saved,
      cart: { ...structuredClone(DEFAULT_DB).cart, ...(saved.cart || {}) },
      session: { ...structuredClone(DEFAULT_DB).session, ...(saved.session || {}) },
      user: { ...structuredClone(DEFAULT_DB).user, ...(saved.user || {}) },
      promos: saved.promos?.length ? saved.promos : structuredClone(DEFAULT_DB).promos,
    };
  } catch {
    return structuredClone(DEFAULT_DB);
  }
}

let db = loadDb();

export function getDb() {
  return db;
}

export function saveDb() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch (e) {
    console.warn('mockStorage: не удалось сохранить', e);
  }
}

export function resetDb() {
  db = structuredClone(DEFAULT_DB);
  saveDb();
}

export function updateDb(patch) {
  db = { ...db, ...patch };
  saveDb();
  return db;
}