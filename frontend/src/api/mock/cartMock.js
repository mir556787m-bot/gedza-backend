// frontend/src/api/mock/cartMock.js
import { getDb, updateDb, saveDb } from './mockStorage';
import { menuMock } from './menuMock';

const FREE_DELIVERY_THRESHOLD = 4000;
const DELIVERY_PRICE = 150;
const MIN_ORDER = 100;
const BONUS_PERCENT = 0.03;

// ─── Стоп-лист (мок). Чтобы протестировать — добавь сюда plateID. ───
const MOCK_STOP_LIST = [];
// Например: const MOCK_STOP_LIST = [10001, 10005];

// ═══════════════════════════════════════════════════════════
//  УТИЛИТЫ
// ═══════════════════════════════════════════════════════════

/** Склонение русских существительных: 1 товар, 2 товара, 5 товаров. */
function pluralRu(n, one, few, many) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

function findMenuItem(plateId) {
  return menuMock().find(
    (m) =>
      String(m.plateID) === String(plateId) ||
      String(m.id) === String(plateId)
  );
}

function calculateTotals(db) {
  const plates = db.cart.plates || [];
  const additions = db.cart.additions || [];
  const total = plates.reduce((sum, p) => sum + p.price * p.count, 0);
  const addonsTotal = additions.reduce((sum, a) => sum + a.price * a.count, 0);
  return { total, addonsTotal };
}

/**
 * ⚡ Фильтр промокодов по типу доставки.
 * delivery_types: "1" — pickup, "2" — delivery.
 * Если не указан — показываем всегда.
 */
function _promoMatchesDelivery(promo, deliveryType) {
  const dt = String(promo.delivery_types || '').trim();
  if (!dt) return true;
  return dt
    .split(',')
    .map((s) => s.trim())
    .includes(String(deliveryType));
}

/**
 * ⚡ Фильтр промокодов по категории товаров в корзине.
 */
function _promoMatchesCategory(promo, cartCategories) {
  const cat = promo.category_name;
  if (!cat) return true;
  return cartCategories.has(cat);
}

/**
 * ⚡ Определяет применённые промокоды.
 * Возвращает полный SellKit-совместимый набор полей.
 */
function applyPromoLogic(db) {
  const { total } = calculateTotals(db);
  const { deliveryType } = db.session;
  const dt = deliveryType === 'pickup' ? '1' : '2';

  const plates = db.cart.plates || [];
  const cartCategories = new Set(
    plates.map((p) => p.categoryName).filter(Boolean)
  );

  // ─── 1. Автопромокоды ───
  const autoApplied = [];
  for (const promo of db.promos) {
    if (!promo.auto_activate) continue;
    if (promo.is_hidden) continue;
    if (!_promoMatchesDelivery(promo, dt)) continue;
    if (!_promoMatchesCategory(promo, cartCategories)) continue;
    autoApplied.push(promo);
  }

  // ─── 2. Явные промокоды ───
  const explicitIds = db.cart.promosIdsString
    ? db.cart.promosIdsString.split(',').filter(Boolean)
    : [];
  const autoIds = new Set(autoApplied.map((p) => String(p.id)));
  const explicitApplied = [];
  for (const id of explicitIds) {
    if (autoIds.has(String(id))) continue;
    const promo = db.promos.find((p) => String(p.id) === String(id));
    if (!promo) continue;
    if (!_promoMatchesDelivery(promo, dt)) continue;
    if (!_promoMatchesCategory(promo, cartCategories)) continue;
    explicitApplied.push(promo);
  }

  // ─── 3. Скидка, подарки, применённые акции ───
  let promoDiscount = 0;
  const orderGifts = [];
  const appliedPromos = [];
  const allAppliedPromosSales = [];
  let promoDescription = '';

  for (const promo of [...autoApplied, ...explicitApplied]) {
    const title = promo.code === 'Самовывоз' ? 'Самовывоз' : promo.title;
    appliedPromos.push({ id: String(promo.id), title });
    allAppliedPromosSales.push({
      id: String(promo.id),
      title,
      sale: String(promo.percent || promo.discount || 0),
      promocodeType: promo.type === 'gift' ? 14 : 13,
      gifts: '',
      iikoId: null,
    });

    if (promo.percent > 0) {
      let base = total;
      if (promo.applies_to_category_only && promo.category_name) {
        base = plates
          .filter((p) => p.categoryName === promo.category_name)
          .reduce((s, p) => s + p.price * p.count, 0);
      }
      promoDiscount += Math.round((base * promo.percent) / 100);
    } else if (promo.discount > 0) {
      if (promo.discount < 1) {
        promoDiscount += Math.round(total * promo.discount);
      } else {
        promoDiscount += promo.discount;
      }
    }

    if (promo.type === 'gift' && promo.giftName) {
      if (total >= (promo.minTotal || 0)) {
        orderGifts.push({
          plateID: promo.giftPlateId || 999,
          plateName: promo.giftName,
          thumbnailPicture: promo.giftImage,
          mass: '250 г',
          isGift: true,
          price: '0',
        });
      }
    }

    if (!promoDescription) {
      promoDescription = promo.description || '';
    }
  }

  return {
    usingPromocode: appliedPromos.length > 0,
    appliedPromos,
    allAppliedPromosSales,
    promoDescription,
    promoDiscount,
    orderGifts,
    autoAppliedIds: autoIds,
  };
}

// ═══════════════════════════════════════════════════════════
//  ЧТЕНИЕ КОРЗИНЫ
// ═══════════════════════════════════════════════════════════

export async function cartGetMock(userId) {
  const db = getDb();
  const { total, addonsTotal } = calculateTotals(db);
  const promoData = applyPromoLogic(db);

  const isPickup = db.session.deliveryType === 'pickup';
  const deliveryType = isPickup ? '1' : '2';
  const isFreeDelivery = total >= FREE_DELIVERY_THRESHOLD;
  const deliveryPrice = isPickup || isFreeDelivery ? 0 : DELIVERY_PRICE;

  const plates = (db.cart.plates || []).map((p) => ({
    id: p.id ?? p.plateID,
    plateID: p.plateID,
    count: p.count,
    price: String(p.price),
    modifiers: '',
    modifiersIds: '{"data":[]}',
    mass: p.mass || '',
    comment: '',
    isFromRecomendations: '0',
    cannotOrderNow: MOCK_STOP_LIST.includes(Number(p.plateID)),
    needToDelete: MOCK_STOP_LIST.includes(Number(p.plateID)),
    timeTags: [],
    categoryID: '',
    subCategoryID: '0',
    sku: p.plateID,
    categoryName: p.categoryName || '',
    cleanPrice: String(p.price),
    modifiersPrice: '0',
    maxCount: 99,
    canHaveSale: '1',
    plateName: p.plateName,
    isForBonuses: '0',
    canSumWithGifts: '1',
    canSumWithPromos: '1',
    canSumWithBonuses: '1',
    thumbnailPicture: p.thumbnailPicture,
    gifts: [],
  }));

  const additions = (db.cart.additions || []).map((a) => ({
    id: String(a.id),
    title: a.title,
    maxCount: 120,
    freeCount: 0,
    price: String(a.price),
    priceDescription: `${a.price}₽`,
    picture: a.picture,
    count: a.count,
  }));

  const fill = Math.min(1, total / FREE_DELIVERY_THRESHOLD);
  const left = Math.max(0, FREE_DELIVERY_THRESHOLD - total);
  const deliveryBanner = {
    isShow: total < FREE_DELIVERY_THRESHOLD && total > 0 && !isPickup,
    title: `еще ${left} ₽`,
    subtitle: 'и доставка будет бесплатная',
    fill: fill.toFixed(4),
  };

  const finalTotal = Math.round(
    total + addonsTotal + deliveryPrice - promoData.promoDiscount
  );
  const bonusEarned = Math.round(finalTotal * BONUS_PERCENT);

  // ⚡ Строки чека — порядок по ТЗ «Блок 3»
  const platesCount = plates.reduce((s, p) => s + p.count, 0);
  const platesWord = pluralRu(platesCount, 'товар', 'товара', 'товаров');

  const allPrices = [];

  // 1. Начислим баллы
  if (bonusEarned > 0) {
    allPrices.push({
      title: 'Начислим баллы',
      value: `+${bonusEarned}`,
      isBonuses: true,
    });
  }

  // 2. Товары
  if (platesCount > 0) {
    allPrices.push({
      title: `${platesCount} ${platesWord}`,
      value: `${Math.round(total)} ₽`,
      isBonuses: false,
    });
  }

  // 3. Платные дополнения
  if (addonsTotal > 0) {
    allPrices.push({
      title: 'Платные дополнения',
      value: `${Math.round(addonsTotal)} ₽`,
      isBonuses: false,
    });
  }

  // 4. Скидка
  if (promoData.promoDiscount > 0) {
    allPrices.push({
      title: 'Скидка',
      value: `-${promoData.promoDiscount} ₽`,
      isBonuses: false,
    });
  }

  // 5. Доставка
  if (deliveryPrice > 0) {
    allPrices.push({
      title: 'Доставка',
      value: `${deliveryPrice} ₽`,
      isBonuses: false,
    });
  }

  const recomendations = menuMock()
    .slice(0, 6)
    .map((m) => ({
      plateID: m.plateID,
      name: m.name,
      price: String(m.price),
      thumbnailPicture: m.image,
    }));

  const activeIds = db.cart.promosIdsString
    ? new Set(db.cart.promosIdsString.split(',').filter(Boolean))
    : new Set();

  const cartCategoriesForFilter = new Set(
    plates.map((pl) => pl.categoryName).filter(Boolean)
  );

  const availablePromos = db.promos
    .filter((p) => !p.is_hidden)
    .filter((p) => _promoMatchesDelivery(p, deliveryType))
    .filter((p) => _promoMatchesCategory(p, cartCategoriesForFilter))
    .map((p) => {
      const pid = String(p.id);
      const isSelected =
        activeIds.has(pid) || promoData.autoAppliedIds.has(pid);
      return {
        id: pid,
        promocode: p.code,
        title: p.title || p.code,
        description: p.description || '',
        tag: p.tag || 'Промокод',
        selected: isSelected,
      };
    });

  const autoPromocodes = {
    title: 'Вам доступны промокоды!',
    promocodes: availablePromos,
  };

  return {
    plates,
    additions,
    orderGifts: promoData.orderGifts,

    platesPrice: String(Math.round(total)),
    platesPriceTitle: `${platesCount} ${platesWord} на ${Math.round(total)} ₽`,
    additionsPrice: Math.round(addonsTotal),
    additionsCount: additions.reduce((s, a) => s + a.count, 0),
    paidAdditionsCount: additions.reduce((s, a) => s + a.count, 0),

    deliveryType,
    deliveryTime: '~ 90 мин',
    deliveryMinutes: 90,
    restaurantId: isPickup ? 1 : null,
    addressTitleCart: isPickup
      ? `Самовывоз на ${db.session.address}`
      : `Доставка на ${db.session.address}`,
    addressTitle: db.session.address,
    addressSubtitle: isPickup
      ? db.session.addressFull
      : db.session.addressFull || 'Доставка',
    addressFull: db.session.addressFull,
    deliveryPriceBanner: deliveryBanner,

    orderComment: db.cart.orderComment || '',
    orderDateTime: db.cart.orderDateTime || 'now',
    orderDateTimeText:
      db.cart.orderDateTime === 'now'
        ? 'Как можно быстрее'
        : db.cart.orderDateTime,
    orderDateTimeTextNew: 'Когда оформить заказ',
    canPreorder: true,
    canOrderNow: true,

    lastOrderPaymentType: db.cart.lastOrderPaymentType || '-1',
    lastOrderPaymentTypeType: '-1',
    lastOrderPaymentTitle:
      {
        cash: 'Наличными',
        card_on_delivery: 'Картой при получении',
        card_online: 'Картой онлайн',
      }[db.cart.lastOrderPaymentType] || 'Не выбрано',
    orderPaymentTypes: [
      { paymentType: '15', type: '0', title: 'Наличные', isNeedToChangeCash: false },
      { paymentType: '16', type: '1', title: 'Картой при получении', isNeedToChangeCash: false },
      { paymentType: '17', type: '2', title: 'Картой онлайн', isNeedToChangeCash: false },
    ],

    promosIdsString: db.cart.promosIdsString || '',
    usingPromocode: promoData.usingPromocode,
    canHavePromocode: true,
    autoPromocodes,
    appliedPromos: {
      title: 'Примененные акции',
      promos: promoData.appliedPromos,
    },
    allAppliedPromosSales: promoData.allAppliedPromosSales,
    promoDescription: promoData.promoDescription,
    promoDiscount: promoData.promoDiscount,

    recomendations,
    recommendationsTitle: 'Что-нибудь еще?',

    isCanGetBonuses: false,
    isCanPayByBonuses: false,
    bonusesToPay: '0',
    bonusesToGet: String(bonusEarned),
    bonusEarned,
    userBonuses: '0',

    allPrices,
    totalPrice: String(Math.round(total)),
    saleTotalPrice: String(finalTotal),

    canOrder: plates.length > 0 && !plates.some((p) => p.cannotOrderNow),
    correctMinPrice: true,
    orderMinPrice: '0',

    orderPopup: {
      isHave: true,
      title: '',
      text: 'Соевый соус, имбирь и васаби продаются отдельно',
      restrictOrder: false,
      buttonContinue: 'Понятно',
      buttonClose: 'Вернуться',
    },
  };
}

// ═══════════════════════════════════════════════════════════
//  ИЗМЕНЕНИЕ КОРЗИНЫ
// ═══════════════════════════════════════════════════════════

export async function cartChangeMock(userId, plateId, count) {
  const db = getDb();
  const menuItem = findMenuItem(plateId);
  if (!menuItem) throw new Error('Товар не найден');

  const existing = db.cart.plates.find(
    (p) => String(p.plateID) === String(plateId)
  );

  if (count <= 0) {
    db.cart.plates = db.cart.plates.filter(
      (p) => String(p.plateID) !== String(plateId)
    );
  } else if (existing) {
    existing.count = count;
  } else {
    db.cart.plates.push({
      plateID: menuItem.plateID,
      plateName: menuItem.name,
      thumbnailPicture: menuItem.image,
      mass: menuItem.mass,
      count,
      price: menuItem.price,
      categoryName: menuItem.category || '',
    });
  }
  saveDb();
  return { success: true };
}

export async function cartRemoveMock(userId, plateId) {
  const db = getDb();
  db.cart.plates = db.cart.plates.filter(
    (p) => String(p.plateID) !== String(plateId)
  );
  saveDb();
  return { success: true };
}

export async function cartClearMock(userId) {
  const db = getDb();
  db.cart.plates = [];
  db.cart.additions = [];
  db.cart.promoCode = null;
  db.cart.promosIdsString = '';
  saveDb();
  return { success: true };
}

export async function cartCommentMock(userId, comment) {
  const db = getDb();
  db.cart.orderComment = comment;
  saveDb();
  return { success: true };
}

export async function cartPaymentMock(userId, paymentType) {
  const db = getDb();
  db.cart.lastOrderPaymentType = paymentType;
  saveDb();
  return { success: true };
}

export async function cartDatetimeMock(userId, datetime) {
  const db = getDb();
  db.cart.orderDateTime = datetime;
  saveDb();
  return { success: true };
}

export async function cartPromoAddMock(userId, code) {
  const db = getDb();
  const promo = db.promos.find(
    (p) => p.code.toUpperCase() === code.toUpperCase()
  );
  if (!promo) {
    return { isHave: false, message: 'Промокод не найден' };
  }
  db.cart.promosIdsString = String(promo.id);
  db.cart.promoCode = promo.code;
  saveDb();
  return {
    isHave: true,
    code: promo.code,
    promosIdsString: db.cart.promosIdsString,
  };
}

export async function cartPromoDeleteMock(userId) {
  const db = getDb();
  db.cart.promoCode = null;
  db.cart.promosIdsString = '';
  saveDb();
  return { success: true };
}

export async function cartTogglePromoMock(userId, promoId) {
  const db = getDb();
  const pid = String(promoId);
  const current = (db.cart.promosIdsString || '').split(',').filter(Boolean);

  let next;
  let action;

  if (current.includes(pid)) {
    next = current.filter((x) => x !== pid);
    action = 'removed';
  } else {
    next = [pid];
    action = 'added';
  }

  db.cart.promosIdsString = next.join(',');
  db.cart.promoCode = next.length
    ? db.promos.find((p) => String(p.id) === next[0])?.code || null
    : null;
  saveDb();

  return {
    success: true,
    promosIdsString: db.cart.promosIdsString,
    action,
    toggledId: promoId,
  };
}

export async function cartAdditionMock(userId, additionId, delta) {
  const db = getDb();
  const existing = db.cart.additions.find(
    (a) => String(a.id) === String(additionId)
  );
  if (existing) {
    existing.count = Math.max(0, existing.count + delta);
    if (existing.count === 0) {
      db.cart.additions = db.cart.additions.filter(
        (a) => String(a.id) !== String(additionId)
      );
    }
  } else if (delta > 0) {
    const menuItem = menuMock().find(
      (m) => String(m.id) === String(additionId)
    );
    if (menuItem) {
      db.cart.additions.push({
        id: menuItem.id,
        title: menuItem.name,
        picture: menuItem.image,
        price: menuItem.price,
        count: delta,
      });
    }
  }
  saveDb();
  return { success: true };
}

export async function cartAvailablePromosMock(userId) {
  const db = getDb();
  return {
    promos: db.promos
      .filter((p) => !p.is_hidden)
      .map((p) => ({
        id: String(p.id),
        promocode: p.code,
        title: p.title,
        description: p.description,
        tag: p.tag,
      })),
  };
}

// ═══════════════════════════════════════════════════════════
//  ОФОРМЛЕНИЕ ЗАКАЗА
// ═══════════════════════════════════════════════════════════

export async function cartCreateOrderMock(userId, phone, address, marketingConsent) {
  const db = getDb();
  const { total, addonsTotal } = calculateTotals(db);
  const promoData = applyPromoLogic(db);
  const isPickup = db.session.deliveryType === 'pickup';
  const deliveryPrice =
    isPickup || total >= FREE_DELIVERY_THRESHOLD ? 0 : DELIVERY_PRICE;
  const finalTotal = Math.round(
    total + addonsTotal + deliveryPrice - promoData.promoDiscount
  );
  const bonusEarned = Math.round(finalTotal * BONUS_PERCENT);

  if (db.cart.plates.length === 0) {
    throw new Error('Корзина пуста');
  }

  const blocked = db.cart.plates.filter((p) =>
    MOCK_STOP_LIST.includes(Number(p.plateID))
  );
  if (blocked.length > 0) {
    throw new Error(
      `Товары недоступны: ${blocked.map((p) => p.plateName).join(', ')}`
    );
  }

  const order = {
    id: 101000 + db.orders.length + 1,
    status: 'pending',
    statusText: 'В ОЖИДАНИИ',
    createdAt: new Date().toLocaleString('ru-RU'),
    total: finalTotal,
    appliedPromos: promoData.appliedPromos.map((p) => p.title),
    bonusEarned,
    deliveryType: db.session.deliveryType,
    address: db.session.addressFull,
    deliveryTime:
      db.cart.orderDateTime === 'now'
        ? 'Как можно быстрее ~ 90 мин'
        : db.cart.orderDateTime,
    paymentMethod:
      {
        cash: 'Наличными',
        card_on_delivery: 'Картой при получении',
        card_online: 'Картой онлайн',
      }[db.cart.lastOrderPaymentType] || 'Не выбрано',
    items: db.cart.plates.map((p) => ({
      id: p.plateID,
      name: p.plateName,
      mass: p.mass,
      count: p.count,
      price: p.price,
      image: p.thumbnailPicture,
    })),
  };

  db.orders.unshift(order);
  db.user.bonus += bonusEarned;
  db.cart.plates = [];
  db.cart.additions = [];
  db.cart.promoCode = null;
  db.cart.promosIdsString = '';
  saveDb();

  return { success: true, order, order_id: String(order.id) };
}

// ═══════════════════════════════════════════════════════════
//  СТОП-ЛИСТ
// ═══════════════════════════════════════════════════════════

export async function cartStopListMock(userId) {
  const db = getDb();
  const cartIds = (db.cart.plates || []).map((p) => String(p.plateID));
  const inStop = cartIds.filter((id) => MOCK_STOP_LIST.includes(Number(id)));
  return { stoplist: inStop };
}