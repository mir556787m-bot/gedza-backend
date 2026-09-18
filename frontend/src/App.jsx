// frontend/src/App.jsx
import { useEffect, useState } from 'react';
import { fetchMenu, updateCart, fetchCart, createOrder } from './api';
import Cart from './components/Cart';
import './App.css';

function App() {
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userId, setUserId] = useState(null);
  const [cartItems, setCartItems] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // === Инициализация пользователя через MAX Bridge ===
  useEffect(() => {
    const initUser = () => {
      if (window.WebApp) {
        window.WebApp.ready();
        const user = window.WebApp.initDataUnsafe?.user;
        if (user) {
          console.log('[MAX] Пользователь:', user.first_name, 'ID:', user.id);
          setUserId(user.id);
          return;
        }
      }
      console.warn('[MAX] Bridge не найден, тестовый ID');
      setUserId(12345);
    };
    initUser();
  }, []);

  // === Загрузка меню и корзины ===
  useEffect(() => {
    if (!userId) return;

    const loadAll = async () => {
      try {
        setLoading(true);
        const menuData = await fetchMenu();
        setMenu(menuData);

        const cartData = await fetchCart(userId);
        const items = buildCartItems(cartData, menuData);
        setCartItems(items);
      } catch (err) {
        console.error(err);
        setError('Не удалось загрузить данные.');
      } finally {
        setLoading(false);
      }
    };
    loadAll();
  }, [userId]);

  const buildCartItems = (cartData, menuData) => {
    if (!cartData || typeof cartData !== 'object') return [];
    if (Array.isArray(cartData.items)) return cartData.items;

    return Object.entries(cartData)
      .map(([itemId, qty]) => {
        const menuItem = menuData.find((m) => m.id === itemId);
        if (!menuItem) return null;
        return { menu_item: menuItem, quantity: Number(qty) };
      })
      .filter(Boolean);
  };

  const refreshCart = async () => {
    if (!menu.length) return;
    try {
      const cartData = await fetchCart(userId);
      const items = buildCartItems(cartData, menu);
      setCartItems(items);
    } catch (err) {
      console.error('Ошибка корзины:', err);
    }
  };

  const handleAddToCart = async (itemId) => {
    try {
      await updateCart(userId, itemId, 1);
      await refreshCart();
    } catch (err) {
      console.error('Ошибка добавления:', err);
    }
  };

  const handleChangeQty = async (itemId, delta) => {
    try {
      await updateCart(userId, itemId, delta);
      await refreshCart();
    } catch (err) {
      console.error('Ошибка изменения количества:', err);
    }
  };

  const handleCheckout = async ({ address, phone, comment }) => {
    try {
      const result = await createOrder(userId, address, phone, comment);
      alert(`Заказ ${result.order_id} принят!\nСумма: ${result.total} ₽`);
      setCartOpen(false);
      await refreshCart();
    } catch (err) {
      console.error('Ошибка заказа:', err);
      alert('Не удалось оформить заказ. Попробуйте еще раз.');
    }
  };

  // === Категории ===
  const categories = ['all', ...new Set(menu.map((item) => item.category).filter(Boolean))];
  const filteredMenu =
    selectedCategory === 'all' ? menu : menu.filter((item) => item.category === selectedCategory);

  // === Подсчёты ===
  const totalItems = cartItems.reduce((sum, i) => sum + i.quantity, 0);
  const totalPrice = cartItems.reduce(
    (sum, i) => sum + i.menu_item.price * i.quantity,
    0
  );

  if (loading) return <div className="loader">Загрузка меню...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="app">
      <header className="header">
        <h1>Доставка Гедзы</h1>
        <span className="user-id">ID: {userId}</span>
      </header>

      {/* Панель категорий */}
      <div className="categories">
        {categories.map((cat) => (
          <button
            key={cat}
            className={`category-btn ${selectedCategory === cat ? 'active' : ''}`}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat === 'all' ? 'Все' : cat}
          </button>
        ))}
      </div>

      <div className="feed">
        {filteredMenu.map((item) => (
          <div key={item.id} className="card">
            <img src={item.image} alt={item.name} className="card-image" />

            {/* Бейдж */}
            {item.badge && (
              <span className={`card-badge card-badge-${item.badge.toLowerCase()}`}>
                {item.badge}
              </span>
            )}

            <div className="card-content">
              <h2 className="card-title">{item.name}</h2>
              {item.weight && <span className="card-weight">{item.weight}</span>}
              {item.description && <p className="card-desc">{item.description}</p>}
              <div className="card-footer">
                <div className="price-block">
                  {item.old_price && <span className="old-price">{item.old_price} ₽</span>}
                  <span className="card-price">{item.price} ₽</span>
                </div>
                <button className="add-btn" onClick={() => handleAddToCart(item.id)}>
                  +
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalItems > 0 && (
        <div className="floating-cart" onClick={() => setCartOpen(true)}>
          <span>🛒 Корзина</span>
          <span className="cart-count">{totalItems}</span>
          <span className="cart-sum">{totalPrice} ₽</span>
        </div>
      )}

      {cartOpen && (
        <Cart
          items={cartItems}
          total={totalPrice}
          onClose={() => setCartOpen(false)}
          onChangeQty={handleChangeQty}
          onCheckout={handleCheckout}
        />
      )}
    </div>
  );
}

export default App;