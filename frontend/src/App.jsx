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

  useEffect(() => {
    const initUser = () => {
      if (window.MAXBridge) {
        window.MAXBridge.ready();
        const user = window.MAXBridge.initDataUnsafe?.user;
        if (user) { setUserId(user.id); return; }
      }
      setUserId(12345);
    };
    initUser();
  }, []);

  useEffect(() => {
    const loadMenu = async () => {
      try {
        setLoading(true);
        const data = await fetchMenu();
        setMenu(data);
      } catch (err) {
        setError("Не удалось загрузить меню.");
      } finally {
        setLoading(false);
      }
    };
    if (userId) loadMenu();
  }, [userId]);

  const refreshCart = async () => {
    try {
      const cart = await fetchCart(userId);
      setCartItems(cart.items || []);
    } catch (err) {
      console.error("Ошибка загрузки корзины:", err);
    }
  };

  useEffect(() => {
    if (userId) refreshCart();
  }, [userId]);

  const handleAddToCart = async (itemId) => {
    try {
      await updateCart(userId, itemId, 1);
      await refreshCart();
    } catch (err) {
      console.error("Ошибка добавления:", err);
    }
  };

  const handleChangeQty = async (itemId, delta) => {
    try {
      await updateCart(userId, itemId, delta);
      await refreshCart();
    } catch (err) {
      console.error("Ошибка изменения количества:", err);
    }
  };

  const handleCheckout = async ({ address, phone, comment }) => {
    try {
      const result = await createOrder(userId, address, phone, comment);
      alert(`Заказ ${result.order_id} принят!\nСумма: ${result.total} ₽`);
      setCartOpen(false);
      await refreshCart();
    } catch (err) {
      console.error("Ошибка заказа:", err);
      alert("Не удалось оформить заказ. Попробуйте еще раз.");
    }
  };

  const totalItems = cartItems.reduce((sum, i) => sum + i.quantity, 0);
  const totalPrice = cartItems.reduce((sum, i) => sum + i.menu_item.price * i.quantity, 0);

  if (loading) return <div className="loader">Загрузка меню...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="app">
      <header className="header">
        <h1>Доставка Гедзы</h1>
        <span className="user-id">ID: {userId}</span>
      </header>

      <div className="feed">
        {menu.map((item) => (
          <div key={item.id} className="card">
            <img src={item.image} alt={item.name} className="card-image" />
            <div className="card-content">
              <h2 className="card-title">{item.name}</h2>
              {item.description && <p className="card-desc">{item.description}</p>}
              <div className="card-footer">
                <span className="card-price">{item.price} ₽</span>
                <button className="add-btn" onClick={() => handleAddToCart(item.id)}>+</button>
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