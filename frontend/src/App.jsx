// frontend/src/App.jsx
import { useEffect, useState, useRef, useCallback } from 'react';
import {
  fetchMenu,
  cartGet,
  cartChange,
  registerUser,
  getUserProfile,
  getSession,
  getOrderHistory,
  reorder,
  loginWithInitData,
} from './api';
import Cart from './components/Cart';
import ProductModal from './components/ProductModal';
import SplashScreen from './components/SplashScreen';
import LocationSheet from './components/LocationSheet';
import RegisterSheet from './components/RegisterSheet';
import ConditionsSheet from './components/ConditionsSheet';
import WheelBanner from './components/WheelBanner';
import WheelModal from './components/WheelModal';
import OrderStatusSheet from './components/OrderStatusSheet';
import ScooterIcon from './components/ScooterIcon';
import './App.css';

const FREE_DELIVERY_THRESHOLD = 4000;
const CATEGORY_ORDER = [
  'Комбо', 'Роллы по 250', 'Роллы по 350', 'Роллы по 450',
  'Фирменные роллы', 'Роллы Прайм', 'Пиццы 25см', 'Пиццы 33 см',
  'Сеты', 'Закуски', 'Горячее и салаты', 'Напитки', 'Десерты', 'Дополнительно',
];

const MENU_RETRY_ATTEMPTS = 15;
const MENU_RETRY_DELAY_MS = 2000;

// ⚡ Сколько попыток ждать initData от MAX Bridge (25 × 200ms = 5 секунд)
const AUTH_WAIT_ATTEMPTS = 25;
const AUTH_WAIT_DELAY_MS = 200;

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userId, setUserId] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [cartData, setCartData] = useState(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [activeCategory, setActiveCategory] = useState(CATEGORY_ORDER[0]);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [categoriesOpen, setCategoriesOpen] = useState(false);
  const [session, setSession] = useState(null);
  const [conditionsOpen, setConditionsOpen] = useState(false);
  const [wheelOpen, setWheelOpen] = useState(false);
  const [userPhone, setUserPhone] = useState('');

  const [locationSheetOpen, setLocationSheetOpen] = useState(false);
  const [profile, setProfile] = useState(null);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [pendingItemId, setPendingItemId] = useState(null);
  const [profileChecked, setProfileChecked] = useState(false);

  const [orders, setOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderStatusOpen, setOrderStatusOpen] = useState(false);

  const feedRef = useRef(null);
  const tabsRef = useRef(null);
  const categoryRefs = useRef({});
  const tabRefs = useRef({});
  const suppressObserver = useRef(false);

  useEffect(() => {
    const t = setTimeout(() => setShowSplash(false), 1500);
    return () => clearTimeout(t);
  }, []);

  // ⚡ Инициализация: WebApp ready + auth (с ожиданием initData)
  useEffect(() => {
    const initUser = async () => {
      let uid = null;
      let initData = '';
      let user = null;

      // ⚡ Ждём готовности MAX Bridge (до 5 секунд)
      for (let attempt = 0; attempt < AUTH_WAIT_ATTEMPTS; attempt++) {
        if (window.WebApp) {
          try {
            window.WebApp.ready();
          } catch (e) {}

          initData = window.WebApp.initData || '';
          user = window.WebApp.initDataUnsafe?.user;

          if (initData || user?.id) {
            console.log(`[auth] ✅ готов на попытке ${attempt + 1}`);
            break;
          }
        }

        console.log(`[auth] attempt ${attempt + 1}: initData ещё не готов`);
        await new Promise((r) => setTimeout(r, AUTH_WAIT_DELAY_MS));
      }

      console.log('[auth] финальное состояние:', {
        hasWebApp: !!window.WebApp,
        initDataLength: initData.length,
        userId: user?.id,
      });

      if (user?.id) {
        uid = user.id;
      }
      if (!uid) {
        uid = 12345; // dev fallback
      }
      setUserId(uid);

      // ⚡ Обмен initData на JWT
      try {
        if (initData) {
          const auth = await loginWithInitData();
          console.log('[auth] ✅ logged in as', auth.user_id);
        } else {
          console.warn('[auth] ⚠️ initData пуст — работаем без JWT (dev)');
        }
      } catch (e) {
        console.error('[auth] ❌ login failed:', e);
      } finally {
        setAuthReady(true);
      }
    };
    initUser();
  }, []);

  // ⚡ Слушатель истечения JWT
  useEffect(() => {
    const handler = () => {
      console.warn('[auth] JWT истёк — требуется перезапуск Mini App');
    };
    window.addEventListener('auth:expired', handler);
    return () => window.removeEventListener('auth:expired', handler);
  }, []);

  useEffect(() => {
    if (!userId || !authReady) return;
    const loadAll = async () => {
      try {
        setLoading(true);

        let menuData = [];
        for (let attempt = 0; attempt < MENU_RETRY_ATTEMPTS; attempt++) {
          menuData = await fetchMenu();
          if (menuData && menuData.length > 0) break;
          console.log(`[menu] attempt ${attempt + 1}: пусто, ждём...`);
          await new Promise((r) => setTimeout(r, MENU_RETRY_DELAY_MS));
        }

        if (!menuData || menuData.length === 0) {
          setError('Меню временно недоступно. Обновите страницу через минуту.');
          return;
        }

        setMenu(menuData);

        try {
          const s = await getSession(userId);
          if (s) setSession(s);
        } catch (e) {}

        try {
          const p = await getUserProfile(userId);
          if (p?.profile?.legal_agreed) {
            setProfile(p.profile);
            setUserPhone(p.profile.phone || '');
          } else {
            setProfile(null);
          }
        } catch (e) {
          console.warn('getUserProfile error:', e);
        } finally {
          setProfileChecked(true);
        }

        await refreshCartData();
        await refreshOrders();
      } catch (err) {
        console.error(err);
        setError('Не удалось загрузить данные.');
      } finally {
        setLoading(false);
      }
    };
    loadAll();
  }, [userId, authReady]);

  const refreshCartData = async () => {
    if (!userId) return;
    try {
      const data = await cartGet(userId);
      setCartData(data);
    } catch (e) {
      console.error('Ошибка загрузки cartData:', e);
    }
  };

  const refreshOrders = async () => {
    if (!userId) return;
    try {
      const data = await getOrderHistory(userId);
      setOrders(data.orders || []);
    } catch (e) {
      console.warn('Ошибка загрузки истории заказов:', e);
    }
  };

  const handleAddToCart = async (itemId) => {
    if (!profileChecked) return;
    if (!profile?.legal_agreed) {
      setPendingItemId(itemId);
      setRegisterOpen(true);
      return;
    }
    try {
      const menuItem = menu.find((m) => m.id === itemId || m.plateID === itemId);
      const plateId = menuItem?.plateID || itemId;
      await cartChange(userId, plateId, 1);
      await refreshCartData();
    } catch (err) {
      console.error('Ошибка добавления:', err);
    }
  };

  const handleChangeQty = async (itemId, delta) => {
    try {
      const menuItem = menu.find((m) => m.id === itemId || m.plateID === itemId);
      const plateId = menuItem?.plateID || itemId;
      const current = (cartData?.plates || []).find(
        (p) => String(p.plateID) === String(plateId)
      );
      const newCount = Math.max(0, (current?.count || 0) + delta);
      await cartChange(userId, plateId, newCount);
      await refreshCartData();
    } catch (err) {
      console.error('Ошибка изменения:', err);
    }
  };

  const handleRegisterSave = async ({ name, phone, address, address_details, legal_agreed }) => {
    try {
      const res = await registerUser(userId, phone, address, legal_agreed, name, address_details);
      if (res?.profile) {
        setProfile(res.profile);
        setUserPhone(phone);
      }
      setRegisterOpen(false);

      if (pendingItemId) {
        const menuItem = menu.find((m) => m.id === pendingItemId || m.plateID === pendingItemId);
        const plateId = menuItem?.plateID || pendingItemId;
        await cartChange(userId, plateId, 1);
        await refreshCartData();
        setPendingItemId(null);
      }
    } catch (e) {
      console.error('registerUser error:', e);
      alert('Не удалось сохранить профиль. Попробуйте ещё раз.');
    }
  };

  const handleSessionConfirm = (data) => {
    setLocationSheetOpen(false);

    (async () => {
      if (data) {
        setSession((prev) => ({
          ...(prev || {}),
          delivery_type: data.delivery_type,
          address: data.address,
          address_full: data.address_full,
        }));
      }

      try {
        const s = await getSession(userId);
        if (s) setSession(s);
      } catch (e) {}

      await refreshCartData();
    })();
  };

  const handleCloseLocationSheet = () => setLocationSheetOpen(false);
  const handleOpenAddressFromHeader = () => setLocationSheetOpen(true);

  const handleOpenCart = () => {
    if (!session) {
      setLocationSheetOpen(true);
      return;
    }
    setCartOpen(true);
  };

  const handleScooterClick = () => setConditionsOpen(true);

  const handleOpenProductFromCart = (rec) => {
    const menuItem = menu.find((m) => String(m.plateID) === String(rec.plateID));
    if (menuItem) {
      setCartOpen(false);
      setSelectedProduct(menuItem);
    }
  };

  const handleOpenOrder = (order) => {
    setSelectedOrder(order);
    setOrderStatusOpen(true);
  };

  const handleRepeatOrder = async (order) => {
    try {
      await reorder(userId, order.id || order.order_id);
      await refreshCartData();
      setOrderStatusOpen(false);
      setCartOpen(true);
    } catch (e) {
      console.error('reorder error:', e);
      alert('Не удалось повторить заказ');
    }
  };

  const categories = CATEGORY_ORDER.filter((cat) =>
    menu.some((item) => item.category === cat)
  );

  const groupedMenu = categories.map((cat) => ({
    category: cat,
    items: menu
      .filter((item) => item.category === cat)
      .sort((a, b) => a.name.localeCompare(b.name, 'ru')),
  }));

  const updateActiveCategory = useCallback(() => {
    if (!feedRef.current || categories.length === 0) return;
    const feedTop = feedRef.current.getBoundingClientRect().top;
    const probeY = feedTop + 60;
    let current = categories[0];
    for (const cat of categories) {
      const el = categoryRefs.current[cat];
      if (!el) continue;
      const rect = el.getBoundingClientRect();
      if (rect.top <= probeY) current = cat;
      else break;
    }
    setActiveCategory(current);
  }, [categories]);

  const handleScroll = useCallback(() => {
    if (!feedRef.current) return;
    const st = feedRef.current.scrollTop;
    setShowScrollTop(st > 400);
    if (!suppressObserver.current) updateActiveCategory();
  }, [updateActiveCategory]);

  useEffect(() => {
    if (!tabsRef.current || !activeCategory) return;
    const tab = tabRefs.current[activeCategory];
    if (!tab) return;
    const container = tabsRef.current;
    const tabLeft = tab.offsetLeft;
    const tabWidth = tab.offsetWidth;
    const containerWidth = container.offsetWidth;
    container.scrollTo({
      left: tabLeft - containerWidth / 2 + tabWidth / 2,
      behavior: 'smooth',
    });
  }, [activeCategory]);

  const handleCategoryClick = (cat) => {
    setActiveCategory(cat);
    const el = categoryRefs.current[cat];
    if (!el || !feedRef.current) return;
    suppressObserver.current = true;
    const feedTop = feedRef.current.getBoundingClientRect().top;
    const elTop = el.getBoundingClientRect().top;
    const scrollTarget = feedRef.current.scrollTop + (elTop - feedTop) - 8;
    feedRef.current.scrollTo({ top: scrollTarget, behavior: 'smooth' });
    setTimeout(() => {
      suppressObserver.current = false;
      updateActiveCategory();
    }, 800);
  };

  const scrollToTop = () => {
    if (!feedRef.current) return;
    suppressObserver.current = true;
    feedRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    if (categories.length) setActiveCategory(categories[0]);
    setTimeout(() => { suppressObserver.current = false; }, 800);
  };

  const qtyMap = (cartData?.plates || []).reduce((acc, p) => {
    acc[String(p.plateID)] = p.count;
    return acc;
  }, {});

  const totalItems = (cartData?.plates || []).reduce(
    (sum, p) => sum + (p.count || 0),
    0
  );
  const totalPrice = parseFloat(cartData?.totalPrice || 0);

  const progress = Math.min(1, totalPrice / FREE_DELIVERY_THRESHOLD);
  const isFreeDelivery = totalPrice >= FREE_DELIVERY_THRESHOLD;

  const isPickup = session?.delivery_type === 'pickup';

  const getScooterState = () => {
    if (totalPrice === 0) return 'idle';
    if (isFreeDelivery) return 'state-free';
    if (progress >= 0.31) return 'state-fast';
    return 'state-slow';
  };

  const lastOrder = orders.length > 0 ? orders[0] : null;

  if (showSplash) return <SplashScreen />;
  if (loading) return <div className="loader">Загрузка меню...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="app">
      <header className="header-location">
        <button className="hl-address" onClick={handleOpenAddressFromHeader}>
          <span className="hl-pin">📍</span>
          <span className="hl-text">
            {session?.address || profile?.address || 'Выбрать адрес'}
          </span>
          <span className="hl-arrow">▾</span>
        </button>
      </header>

      <div className="delivery-toggle">
        <button
          className={`delivery-toggle-btn ${!isPickup ? 'active' : ''}`}
          onClick={() => {
            if (isPickup) {
              handleSessionConfirm({ delivery_type: 'delivery' });
              setLocationSheetOpen(true);
            }
          }}
        >
          Доставка
        </button>
        <button
          className={`delivery-toggle-btn ${isPickup ? 'active' : ''}`}
          onClick={() => {
            if (!isPickup) {
              handleSessionConfirm({ delivery_type: 'pickup' });
              setLocationSheetOpen(true);
            }
          }}
        >
          Самовывоз
        </button>
      </div>

      {lastOrder && (
        <div className="last-order-card" onClick={() => handleOpenOrder(lastOrder)}>
          <div className="last-order-header">
            <span className={`last-order-status ${lastOrder.status}`}>
              {lastOrder.statusText}
            </span>
            <span className="last-order-arrow">›</span>
          </div>
          <div className="last-order-body">
            <div className="last-order-info">
              <span className="last-order-title">Заказ #{lastOrder.id}</span>
              <span className="last-order-date">{lastOrder.createdAt}</span>
            </div>
            {lastOrder.items?.[0]?.image && (
              <img
                src={lastOrder.items[0].image}
                alt=""
                className="last-order-img"
              />
            )}
          </div>
          <button
            className="last-order-repeat"
            onClick={(e) => {
              e.stopPropagation();
              handleRepeatOrder(lastOrder);
            }}
          >
            Повторить заказ
          </button>
        </div>
      )}

      <WheelBanner onClick={() => setWheelOpen(true)} />

      <div className="tabs-row">
        <button
          className="tabs-hamburger"
          onClick={() => setCategoriesOpen(true)}
          aria-label="Категории"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 6h18" />
            <path d="M3 12h18" />
            <path d="M3 18h18" />
          </svg>
        </button>
        <div className="categories" ref={tabsRef}>
          {categories.map((cat) => (
            <button
              key={cat}
              ref={(el) => { tabRefs.current[cat] = el; }}
              className={`category-btn ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => handleCategoryClick(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="feed" ref={feedRef} onScroll={handleScroll}>
        {groupedMenu.map(({ category, items }) => (
          <div
            key={category}
            className="category-section"
            data-category={category}
            ref={(el) => { categoryRefs.current[category] = el; }}
          >
            <h2 className="category-title">{category}</h2>
            <div className="grid">
              {items.map((item) => {
                const plateId = item.plateID || item.id;
                const qty = qtyMap[String(plateId)] || 0;
                return (
                  <ProductCard
                    key={item.id}
                    item={item}
                    qty={qty}
                    onAdd={() => handleAddToCart(item.id)}
                    onChangeQty={(delta) => handleChangeQty(item.id, delta)}
                    onOpen={() => setSelectedProduct(item)}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="floating-bottom">
        {totalItems > 0 && (
          <>
            <div className="floating-cart" onClick={handleOpenCart}>
              <span className="cart-icon">🛒</span>
              <span className="cart-count">{totalItems}</span>
              <span className="cart-sum">{totalPrice} ₽</span>
            </div>

            <div className="scooter-wrap">
              {isPickup ? (
                <div
                  className="scooter-container state-box"
                  onClick={handleScooterClick}
                >
                  <div
                    className="scooter-progress-ring"
                    style={{ '--p': progress }}
                  />
                  <div className="scooter-icon-inner">
                    <svg
                      width="26"
                      height="26"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                      <line x1="12" y1="22.08" x2="12" y2="12" />
                    </svg>
                  </div>
                </div>
              ) : (
                <div
                  className={`scooter-container ${getScooterState()}`}
                  onClick={handleScooterClick}
                >
                  <div
                    className="scooter-progress-ring"
                    style={{ '--p': progress }}
                  />
                  <div className="scooter-icon-inner">
                    <ScooterIcon />
                  </div>
                </div>
              )}
            </div>

            {showScrollTop && (
              <button className="scroll-top-btn" onClick={scrollToTop} aria-label="Наверх">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="m5 12 7-7 7 7" />
                  <path d="M12 19V5" />
                </svg>
              </button>
            )}
          </>
        )}
      </div>

      <Cart
        open={cartOpen}
        userId={userId}
        cartData={cartData}
        phone={userPhone}
        onClose={() => setCartOpen(false)}
        onRefresh={async () => {
          await refreshCartData();
          await refreshOrders();
        }}
        onOpenProduct={handleOpenProductFromCart}
        onOrderCreated={() => {
          setCartOpen(false);
          refreshCartData();
          refreshOrders();
        }}
        onSessionUpdated={handleSessionConfirm}
      />

      <ConditionsSheet
        open={conditionsOpen}
        type={isPickup ? 'pickup' : 'delivery'}
        title={session?.address || 'Условия'}
        onClose={() => setConditionsOpen(false)}
      />

      <RegisterSheet
        open={registerOpen}
        initialPhone={userPhone}
        onSave={handleRegisterSave}
        onClose={() => {
          setRegisterOpen(false);
          setPendingItemId(null);
        }}
      />

      <ProductModal
        open={!!selectedProduct}
        product={selectedProduct}
        qty={
          selectedProduct
            ? qtyMap[String(selectedProduct.plateID || selectedProduct.id)] || 0
            : 0
        }
        onClose={() => setSelectedProduct(null)}
        onAdd={() => handleAddToCart(selectedProduct.id)}
        onChangeQty={(delta) => handleChangeQty(selectedProduct.id, delta)}
        onOpenCart={() => {
          setSelectedProduct(null);
          setCartOpen(true);
        }}
      />

      <WheelModal
        open={wheelOpen}
        userId={userId}
        onClose={() => setWheelOpen(false)}
        onPrizeWon={(result) => {
          console.log('Приз выигран:', result);
        }}
      />

      <OrderStatusSheet
        open={orderStatusOpen}
        order={selectedOrder}
        onClose={() => setOrderStatusOpen(false)}
        onRepeat={handleRepeatOrder}
      />

      {locationSheetOpen && (
        <LocationSheet
          userId={userId}
          currentType={session?.delivery_type || 'delivery'}
          open={locationSheetOpen}
          onConfirm={handleSessionConfirm}
          onClose={handleCloseLocationSheet}
        />
      )}

      {categoriesOpen && (
        <div className="cats-overlay" onClick={() => setCategoriesOpen(false)}>
          <div className="cats-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="cats-header">
              <h2>Все категории</h2>
              <button className="close-btn" onClick={() => setCategoriesOpen(false)}>✕</button>
            </div>
            <div className="cats-list">
              {categories.map((cat) => (
                <button
                  key={cat}
                  className={`cats-item ${activeCategory === cat ? 'active' : ''}`}
                  onClick={() => {
                    setCategoriesOpen(false);
                    handleCategoryClick(cat);
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProductCard({ item, qty, onAdd, onChangeQty, onOpen }) {
  const inCart = qty > 0;
  return (
    <div className="product-card">
      <div className="product-image-wrap" onClick={onOpen}>
        <img src={item.image} alt={item.name} className="product-image" loading="lazy" />
        {item.badge && (
          <span className={`product-badge badge-${item.badge.toLowerCase()}`}>
            {item.badge}
          </span>
        )}
        {inCart && <span className="product-qty-on-image">{qty}</span>}
      </div>
      <div className="product-body">
        <h3 className="product-name" onClick={onOpen}>{item.name}</h3>
        {item.weight && <span className="product-weight">{item.weight}</span>}
        <div className="product-footer">
          {!inCart ? (
            <button
              className="add-btn-light"
              onClick={(e) => { e.stopPropagation(); onAdd(); }}
            >
              {item.price} ₽ +
            </button>
          ) : (
            <div className="qty-control" onClick={(e) => e.stopPropagation()}>
              <button className="qty-btn" onClick={() => onChangeQty(-1)}>−</button>
              <span className="qty-value">{item.price} ₽</span>
              <button className="qty-btn" onClick={() => onChangeQty(1)}>+</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;