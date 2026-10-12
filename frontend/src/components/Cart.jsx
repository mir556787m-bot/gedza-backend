// frontend/src/components/Cart.jsx
import { useState, useEffect, useMemo, useCallback } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import {
  cartChange,
  cartRemove,
  cartDatetime,
  cartPromoAdd,
  cartAddition,
  cartCreateOrder,
  cartTogglePromo,
  cartClearPromos,
  cartStopList,
  cartPayment,
} from '../api';
import ScooterIcon from './ScooterIcon';
import CommentSheet from './CommentSheet';
import ConditionsSheet from './ConditionsSheet';
import SupportSheet from './SupportSheet';
import PreorderSheet from './PreorderSheet';
import PaymentSheet from './PaymentSheet';
import LocationSheet from './LocationSheet';
import PromoTicket from './PromoTicket';
import './Cart.css';

const FREE_DELIVERY_THRESHOLD = 4000;
const DELIVERY_PRICE = 150;
const MIN_ORDER = 100;

const PAYMENT_LABELS = {
  cash: 'Наличными',
  card_on_delivery: 'Картой при получении',
  card_online: 'Картой онлайн',
  '15': 'Наличными',
  '16': 'Картой при получении',
  '17': 'Картой онлайн',
};

export default function Cart({
  open,
  userId,
  cartData,
  phone: userPhone,
  onClose,
  onRefresh,
  onOpenProduct,
  onOrderCreated,
  onSessionUpdated,
}) {
  const [preorderSheetOpen, setPreorderSheetOpen] = useState(false);
  const [paymentSheetOpen, setPaymentSheetOpen] = useState(false);
  const [locationSheetOpen, setLocationSheetOpen] = useState(false);

  const [promoOpen, setPromoOpen] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [noCallback, setNoCallback] = useState(true);
  const [persons, setPersons] = useState(1);
  const [commentOpen, setCommentOpen] = useState(false);
  const [conditionsOpen, setConditionsOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [orderPlaced, setOrderPlaced] = useState(false);
  const [stopList, setStopList] = useState([]);

  const [optimisticPromoId, setOptimisticPromoId] = useState(null);

  const { scrollRef } = useScrollPosition({ isEnabled: open });

  useEffect(() => {
    if (!open) {
      setOrderPlaced(false);
      setPromoCode('');
      setPreorderSheetOpen(false);
      setPaymentSheetOpen(false);
      setLocationSheetOpen(false);
      setOptimisticPromoId(null);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !userId) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await cartStopList(userId);
        if (!cancelled) setStopList(data?.stoplist || []);
      } catch (e) {
        console.warn('stoplist error:', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, userId]);

  if (!cartData) return null;

  const plates = cartData.plates || [];
  const additions = (cartData.additions || []).filter(
    (a) => !/палочк/i.test(a.title || '')
  );
  const total = parseFloat(cartData.totalPrice || 0);
  const addonsTotal = additions.reduce(
    (sum, a) => sum + (parseFloat(a.price) || 0) * (a.count || 0),
    0
  );

  const stopSet = useMemo(() => new Set(stopList.map(String)), [stopList]);
  const isStopped = useCallback(
    (plateId) => stopSet.has(String(plateId)),
    [stopSet]
  );

  const availableTotal = plates.reduce((sum, p) => {
    if (isStopped(p.plateID)) return sum;
    return sum + parseFloat(p.price) * p.count;
  }, 0);

  const hasStoppedItems = plates.some((p) => isStopped(p.plateID));

  const freeDeliveryProgress = Math.min(
    1,
    availableTotal / FREE_DELIVERY_THRESHOLD
  );
  const isFreeDelivery = availableTotal >= FREE_DELIVERY_THRESHOLD;
  const deliveryPrice = isFreeDelivery ? 0 : DELIVERY_PRICE;
  const promoDiscount = parseFloat(cartData.promoDiscount || 0);

  const finalTotal = parseFloat(
    cartData.saleTotalPrice ||
      availableTotal + addonsTotal + deliveryPrice - promoDiscount
  );

  const freeDeliveryLeft = Math.max(
    0,
    FREE_DELIVERY_THRESHOLD - availableTotal
  );
  const isEmpty = plates.length === 0;

  const paymentLabel =
    cartData.lastOrderPaymentTitle ||
    PAYMENT_LABELS[cartData.lastOrderPaymentType] ||
    'Картой при получении';

  const isPreorder = cartData.orderDateTime && cartData.orderDateTime !== 'now';
  const isPickup =
    cartData.deliveryType === '1' || cartData.deliveryType === 1;

  const timeLabel = isPreorder
    ? cartData.orderDateTimeText
    : `Как можно быстрее ${cartData.deliveryTime || '~ 90 мин'}`;
  const commentText = cartData.orderComment || '';
  const conditionsTitle =
    cartData.addressFull || cartData.addressTitle || 'Условия';

  const orderGifts = cartData.orderGifts || [];
  const autoPromocodes = cartData.autoPromocodes || {
    title: '',
    promocodes: [],
  };
  const promos = autoPromocodes.promocodes || [];
  const usingPromocode = cartData.usingPromocode || false;
  const appliedPromos = cartData.appliedPromos?.promos || [];
  const allPrices = cartData.allPrices || [];
  const promoDescription = cartData.promoDescription || '';

  const receiptRows = allPrices || [];

  const isPromoSelected = useCallback(
    (promo) => {
      if (!promo?.id) return false;
      const pid = String(promo.id);

      if (optimisticPromoId !== null) {
        if (optimisticPromoId === '') return false;
        return optimisticPromoId === pid;
      }

      return Boolean(promo.selected);
    },
    [optimisticPromoId]
  );

  const handleChange = async (plateId, newCount) => {
    await cartChange(userId, plateId, newCount);
    await onRefresh();
  };

  const handleRemove = async (plateId) => {
    await cartRemove(userId, plateId);
    await onRefresh();
  };

  const handleAddonChange = async (additionId, delta) => {
    await cartAddition(userId, additionId, delta);
    await onRefresh();
  };

  const handleTogglePromo = async (promoId) => {
    const pid = String(promoId);
    const promoInList = promos.find((p) => String(p.id) === pid);
    const wasSelected = Boolean(promoInList?.selected);

    setOptimisticPromoId(wasSelected ? '' : pid);

    try {
      await cartTogglePromo(userId, promoId);
      await onRefresh();
    } catch (e) {
      console.error('toggle promo error:', e);
    } finally {
      setOptimisticPromoId(null);
    }
  };

  const handlePromoDelete = async () => {
    setOptimisticPromoId('');
    try {
      await cartClearPromos(userId);
      await onRefresh();
    } catch (e) {
      console.error('clear promos error:', e);
    } finally {
      setOptimisticPromoId(null);
    }
  };

  const handlePromoApply = async (code = promoCode) => {
    if (!code.trim()) return;
    try {
      const result = await cartPromoAdd(userId, code);
      if (result.isHave) {
        setPromoOpen(false);
        setPromoCode('');
        await onRefresh();
      } else {
        alert(result.message || 'Промокод не найден');
      }
    } catch (e) {
      console.error('promo add error:', e);
      alert('Не удалось применить промокод');
    }
  };

  const handlePreorderSelect = async (datetime) => {
    try {
      await cartDatetime(userId, datetime);
      await onRefresh();
    } catch (e) {
      console.error('cartDatetime error:', e);
    }
    setPreorderSheetOpen(false);
  };

  const handlePaymentSelect = async (paymentType) => {
    try {
      await cartPayment(userId, paymentType);
      await onRefresh();
    } catch (e) {
      console.error('cartPayment error:', e);
    }
  };

  const handleLocationConfirm = async (data) => {
    setLocationSheetOpen(false);
    if (onSessionUpdated) await onSessionUpdated(data);
    await onRefresh();
  };

  const handleCheckout = async () => {
    if (isEmpty) return;
    if (hasStoppedItems) {
      alert('Удалите недоступные товары для оформления');
      return;
    }
    if (!userPhone) {
      alert('Телефон не найден. Перезайдите в приложение.');
      return;
    }
    setSubmitting(true);
    try {
      const address = cartData.addressFull || null;
      const result = await cartCreateOrder(userId, userPhone, address, true);
      setOrderPlaced(true);
      onClose();
      if (onOrderCreated) onOrderCreated(result);
    } catch (e) {
      console.error('createOrder error:', e);
      alert(
        e?.response?.data?.detail ||
          e?.message ||
          'Не удалось оформить заказ. Попробуйте ещё раз.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Sheet
        isOpen={open}
        onClose={onClose}
        detent="default"
        dragVelocityThreshold={500}
        dragCloseThreshold={0.25}
        tweenConfig={{ ease: 'easeOut', duration: 0.4 }}
      >
        <Sheet.Container>
          <Sheet.Header />

          <button
            className="cart-close-inline"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ✕
          </button>

          <Sheet.Content scrollRef={scrollRef} scrollClassName="cart-scroll">
            <div className="cart-panel">
              {/* КАРТОЧКА 1: Получение */}
              <div className="cart-card">
                <div
                  className="cart-address"
                  onClick={() => setLocationSheetOpen(true)}
                >
                  <h3 className="cart-address-title">
                    {cartData.addressTitleCart || 'Выбрать адрес'}
                    <span className="arrow-down-icon">⌵</span>
                  </h3>
                  {(cartData.addressSubtitle || cartData.addressFull) && (
                    <p className="cart-address-sub">
                      {isPickup
                        ? cartData.addressSubtitle || cartData.addressFull
                        : cartData.addressFull || cartData.addressSubtitle}
                    </p>
                  )}
                </div>

                <div className="cart-divider" />

                <div
                  className="cart-row"
                  onClick={() => setPreorderSheetOpen(true)}
                >
                  <span className="cart-row-icon">🕒</span>
                  <span className="cart-row-text">{timeLabel}</span>
                  <span className="cart-row-arrow">›</span>
                </div>

                <div className="cart-divider" />

                <div className="cart-toggle-row">
                  <div
                    className={`cart-toggle-slider ${
                      isPreorder ? 'right' : 'left'
                    }`}
                  />
                  <button
                    className={`cart-toggle-btn ${
                      !isPreorder ? 'active' : ''
                    }`}
                    onClick={() =>
                      cartDatetime(userId, 'now').then(onRefresh)
                    }
                  >
                    <span className="cart-toggle-main">Сейчас, побыстрее</span>
                    <span className="cart-toggle-sub">
                      {cartData.deliveryTime || '~ 90 мин'}
                    </span>
                  </button>
                  <button
                    className={`cart-toggle-btn ${
                      isPreorder ? 'active' : ''
                    }`}
                    onClick={() => setPreorderSheetOpen(true)}
                  >
                    <span className="cart-toggle-main">Предзаказ</span>
                    <span className="cart-toggle-sub">
                      {isPreorder
                        ? cartData.orderDateTimeText
                        : 'Выберите время'}
                    </span>
                  </button>
                </div>

                <div className="cart-divider" />

                <div className="cart-row" onClick={() => setCommentOpen(true)}>
                  <span className="cart-row-icon">💬</span>
                  <span className="cart-row-text">
                    {commentText || 'Комментарий'}
                  </span>
                  <span className="cart-row-arrow">›</span>
                </div>

                <div className="cart-divider" />

                <div className="cart-row cart-row-switch">
                  <span className="cart-row-icon">📞</span>
                  <span className="cart-row-text">Не перезванивать</span>
                  <button
                    className={`cart-switch ${noCallback ? 'on' : ''}`}
                    onClick={() => setNoCallback(!noCallback)}
                    role="switch"
                    aria-checked={noCallback}
                  >
                    <span className="cart-switch-knob" />
                  </button>
                </div>
              </div>

              {/* КАРТОЧКА 2: Прогресс */}
              {!isEmpty && !isFreeDelivery && !isPickup && (
                <div className="cart-card">
                  <div
                    className="cart-progress-row"
                    onClick={() => setConditionsOpen(true)}
                  >
                    <div className="cart-progress-icon">
                      <div
                        className="cart-progress-ring"
                        style={{ '--p': freeDeliveryProgress }}
                      />
                      <div className="cart-progress-inner">
                        <ScooterIcon />
                      </div>
                    </div>
                    <div className="cart-progress-text">
                      <span className="cart-progress-amount">
                        еще {freeDeliveryLeft} ₽
                      </span>
                      <span className="cart-progress-hint">
                        и доставка будет бесплатная
                      </span>
                    </div>
                    <span className="cart-progress-info">i</span>
                  </div>
                </div>
              )}

              {/* КАРТОЧКА 3: Товары */}
              {!isEmpty && (
                <div className="cart-card">
                  <div className="cart-items-header">
                    {plates.length} товаров на {total} ₽
                  </div>
                  <div className="cart-items">
                    {plates.map((item) => {
                      const stopped = isStopped(item.plateID);
                      return (
                        <div
                          key={item.plateID}
                          className={`cart-item ${
                            stopped ? 'cart-item-stopped' : ''
                          }`}
                        >
                          <div className="cart-item-img-wrap">
                            <img
                              src={item.thumbnailPicture}
                              alt={item.plateName}
                              className="cart-item-img"
                            />
                            {stopped && (
                              <span className="cart-item-stop-badge">
                                Недоступно для заказа
                              </span>
                            )}
                          </div>
                          <div className="cart-item-body">
                            <div className="cart-item-info">
                              <span className="cart-item-name">
                                {item.plateName}
                              </span>
                              {item.mass && (
                                <span className="cart-item-weight">
                                  {item.mass}
                                </span>
                              )}
                            </div>
                            <div className="cart-item-bottom">
                              <div className="cart-item-qty">
                                <button
                                  className="qty-btn qty-minus"
                                  onClick={() =>
                                    handleChange(item.plateID, item.count - 1)
                                  }
                                >
                                  −
                                </button>
                                <span className="qty-value">{item.count}</span>
                                <button
                                  className="qty-btn qty-plus"
                                  onClick={() =>
                                    handleChange(item.plateID, item.count + 1)
                                  }
                                  disabled={stopped}
                                >
                                  +
                                </button>
                              </div>
                              {!stopped && (
                                <button
                                  className="cart-item-del"
                                  onClick={() => handleRemove(item.plateID)}
                                  aria-label="Удалить"
                                >
                                  <svg
                                    width="20"
                                    height="20"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  >
                                    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                                  </svg>
                                </button>
                              )}
                              <span className="cart-item-sum">
                                {item.price} ₽
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {isEmpty && (
                <div className="cart-card">
                  <div className="cart-empty">
                    <div className="cart-empty-title">Корзина пустая</div>
                    <div className="cart-empty-sub">
                      Скорее добавьте блюда
                    </div>
                  </div>
                </div>
              )}

              {/* ПОДАРКИ */}
              {orderGifts.length > 0 && (
                <div className="cart-card">
                  <div className="cart-section">
                    <div className="cart-section-title">
                      <span className="cart-gift-icon">🎁</span>
                      <span>Подарки</span>
                    </div>
                    <div className="cart-gifts">
                      {orderGifts.map((gift, idx) => (
                        <div key={gift.plateID || idx} className="cart-gift">
                          <img
                            src={gift.thumbnailPicture}
                            alt={gift.plateName}
                            className="cart-gift-img"
                          />
                          <div className="cart-gift-info">
                            <span className="cart-gift-name">
                              {gift.plateName}
                            </span>
                            <span className="cart-gift-label">ПОДАРОК</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ПРОМОКОД */}
              <div className="cart-card">
                <div className="cart-promo">
                  {/* ⚡ Иконка % — 40×40 через inline-style + !important в CSS */}
                  <div className="cart-promo-title">
                    <span
                      className="cart-icon-promo"
                      style={{
                        width: '40px',
                        height: '40px',
                        minWidth: '40px',
                        minHeight: '40px',
                        maxWidth: '40px',
                        maxHeight: '40px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        padding: 0,
                        margin: 0,
                        background: 'transparent',
                        borderRadius: 0,
                      }}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 100 100"
                        width="40"
                        height="40"
                        style={{
                          width: '40px',
                          height: '40px',
                          minWidth: '40px',
                          minHeight: '40px',
                          maxWidth: '40px',
                          maxHeight: '40px',
                          display: 'block',
                        }}
                      >
                        {/* Внешний красный круг */}
                        <circle cx="50" cy="50" r="45" fill="#D31D24" />

                        {/* Розетка: 3 квадрата под углами 0°, 30°, 60° */}
                        <g fill="#FFFFFF">
                          <rect
                            x="26.5"
                            y="26.5"
                            width="47"
                            height="47"
                            rx="2"
                            transform="rotate(0 50 50)"
                          />
                          <rect
                            x="26.5"
                            y="26.5"
                            width="47"
                            height="47"
                            rx="2"
                            transform="rotate(30 50 50)"
                          />
                          <rect
                            x="26.5"
                            y="26.5"
                            width="47"
                            height="47"
                            rx="2"
                            transform="rotate(60 50 50)"
                          />
                        </g>

                        {/* Знак процента */}
                        <g
                          stroke="#D31D24"
                          strokeLinecap="round"
                          fill="none"
                        >
                          <line
                            x1="62"
                            y1="38"
                            x2="38"
                            y2="62"
                            strokeWidth="5.5"
                          />
                          <circle
                            cx="41"
                            cy="41"
                            r="4.5"
                            strokeWidth="4.5"
                          />
                          <circle
                            cx="59"
                            cy="59"
                            r="4.5"
                            strokeWidth="4.5"
                          />
                        </g>
                      </svg>
                    </span>
                    <span>Промокод</span>
                  </div>

                  {/* Поле: ввод или применённый промокод */}
                  {!usingPromocode ? (
                    <button
                      className="cart-promo-btn"
                      onClick={() => setPromoOpen(true)}
                    >
                      + ВВЕСТИ ПРОМОКОД
                    </button>
                  ) : (
                    <>
                      <div className="cart-promo-applied">
                        <span className="cart-promo-applied-status">
                          {appliedPromos.map((ap) => ap.title).join(', ') ||
                            'Промокод применён'}
                        </span>
                        <button onClick={handlePromoDelete}>ОЧИСТИТЬ</button>
                      </div>

                      {promoDescription && (
                        <div className="cart-promo-description">
                          {promoDescription}
                        </div>
                      )}
                    </>
                  )}

                  {/* Карусель доступных промокодов */}
                  {promos.length > 0 && (
                    <div className="cart-promo-carousel">
                      <div className="cart-promo-carousel-title">
                        Вам доступны промокоды!
                      </div>
                      <div className="cart-promo-carousel-track">
                        {promos.map((p) => (
                          <PromoTicket
                            key={p.id || p.promocode}
                            promo={p}
                            selected={isPromoSelected(p)}
                            onClick={() => p.id && handleTogglePromo(p.id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Дополнения */}
              {additions.length > 0 && (
                <div className="cart-card">
                  <div className="cart-section">
                    <div className="cart-section-title">Добавить к заказу</div>
                    <div className="cart-addons">
                      {additions.map((add) => (
                        <div key={add.id} className="cart-addon">
                          <img
                            src={add.picture}
                            alt={add.title}
                            className="cart-addon-img"
                          />
                          <div className="cart-addon-info">
                            <span className="cart-addon-name">{add.title}</span>
                            <span className="cart-addon-price">
                              {add.price} ₽
                            </span>
                          </div>
                          {add.count === 0 ? (
                            <button
                              className="cart-addon-add"
                              onClick={() => handleAddonChange(add.id, 1)}
                            >
                              <span>0</span>
                              <span className="cart-addon-plus">+</span>
                            </button>
                          ) : (
                            <div className="cart-addon-qty">
                              <button
                                onClick={() => handleAddonChange(add.id, -1)}
                              >
                                −
                              </button>
                              <span>{add.count}</span>
                              <button
                                onClick={() => handleAddonChange(add.id, 1)}
                              >
                                +
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Персоны */}
              <div className="cart-card">
                <div className="cart-row-qty">
                  <span className="cart-row-icon">👥</span>
                  <span>Количество персон</span>
                  <div className="cart-qty-control">
                    {persons > 1 && (
                      <button
                        className="qty-btn"
                        onClick={() => setPersons(persons - 1)}
                      >
                        −
                      </button>
                    )}
                    <span>{persons}</span>
                    <button
                      className="qty-btn qty-plus"
                      onClick={() => setPersons(persons + 1)}
                    >
                      +
                    </button>
                  </div>
                </div>
              </div>

              {/* Способ оплаты */}
              <div className="cart-card">
                <div
                  className="cart-row-btn"
                  onClick={() => setPaymentSheetOpen(true)}
                >
                  <div className="cart-row-content">
                    <div className="cart-row-btn-title">Способ оплаты</div>
                    <div className="cart-row-btn-sub">{paymentLabel}</div>
                  </div>
                  <span className="cart-arrow">›</span>
                </div>
              </div>

              {/* Рекомендации */}
              {cartData.recomendations?.length > 0 && (
                <div className="cart-card">
                  <div className="cart-section">
                    <div className="cart-section-title">
                      {cartData.recommendationsTitle || 'Что-нибудь ещё?'}
                    </div>
                    <div className="cart-recommendations">
                      {cartData.recomendations.map((rec) => (
                        <div
                          key={rec.plateID}
                          className="cart-rec-card"
                          onClick={() => onOpenProduct && onOpenProduct(rec)}
                        >
                          <img
                            src={rec.thumbnailPicture}
                            alt={rec.name}
                            className="cart-rec-img"
                          />
                          <span className="cart-rec-name">{rec.name}</span>
                          <span className="cart-rec-price">{rec.price} ₽</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Чек */}
              {!isEmpty && receiptRows.length > 0 && (
                <div className="cart-card">
                  <div className="cart-receipt">
                    {receiptRows.map((row, idx) => {
                      let className = '';
                      if (row.isBonuses || row.title === 'Начислим баллы') {
                        className = 'bonus';
                      } else if (row.title?.startsWith('Скидка')) {
                        className = 'discount';
                      } else if (row.title === 'Доставка') {
                        className = 'delivery';
                      }
                      return (
                        <div
                          key={idx}
                          className={`cart-receipt-row ${className}`}
                        >
                          <span>{row.title}</span>
                          <span>{row.value}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </Sheet.Content>

          {/* Футер */}
          <div className="cart-footer-fixed">
            <div className="cart-footer-row">
              <div className="cart-footer-total">
                <span className="cart-footer-label">К оплате</span>
                <span className="cart-footer-price">
                  {isEmpty ? 0 : finalTotal} ₽
                </span>
              </div>
              <button
                className="checkout-btn"
                disabled={isEmpty || submitting || hasStoppedItems}
                onClick={handleCheckout}
              >
                {submitting ? 'Отправляем...' : 'Оформить заказ'}
              </button>
            </div>

            {hasStoppedItems && (
              <div className="cart-footer-warning">
                Удалите недоступные товары из корзины
              </div>
            )}
          </div>
        </Sheet.Container>
        <Sheet.Backdrop />
      </Sheet>

      {/* Шит ввода промокода вручную */}
      <Sheet
        isOpen={promoOpen}
        onClose={() => setPromoOpen(false)}
        detent="content"
        dragVelocityThreshold={500}
        dragCloseThreshold={0.25}
        tweenConfig={{ ease: 'easeOut', duration: 0.4 }}
      >
        <Sheet.Container>
          <Sheet.Header />
          <Sheet.Content>
            <div className="promo-sheet">
              <button
                className="promo-close"
                onClick={() => setPromoOpen(false)}
                aria-label="Закрыть"
              >
                ✕
              </button>
              <div className="promo-input-row">
                <input
                  className="promo-input"
                  placeholder="Промокод"
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                  autoFocus
                />
                <button
                  className="promo-apply"
                  onClick={() => handlePromoApply()}
                  disabled={!promoCode.trim()}
                >
                  применить
                </button>
              </div>
            </div>
          </Sheet.Content>
        </Sheet.Container>
        <Sheet.Backdrop />
      </Sheet>

      <CommentSheet
        open={commentOpen}
        userId={userId}
        initialValue={commentText}
        onSaved={onRefresh}
        onClose={() => setCommentOpen(false)}
      />

      <ConditionsSheet
        open={conditionsOpen}
        type={isPickup ? 'pickup' : 'delivery'}
        title={conditionsTitle}
        onClose={() => setConditionsOpen(false)}
      />

      <PreorderSheet
        open={preorderSheetOpen}
        onSelect={handlePreorderSelect}
        onClose={() => setPreorderSheetOpen(false)}
      />

      <PaymentSheet
        open={paymentSheetOpen}
        selected={cartData?.lastOrderPaymentType}
        onSelect={handlePaymentSelect}
        onClose={() => setPaymentSheetOpen(false)}
      />

      <LocationSheet
        userId={userId}
        currentType={isPickup ? 'pickup' : 'delivery'}
        open={locationSheetOpen}
        onConfirm={handleLocationConfirm}
        onClose={() => setLocationSheetOpen(false)}
      />

      <SupportSheet
        open={supportOpen}
        onClose={() => setSupportOpen(false)}
      />
    </>
  );
}