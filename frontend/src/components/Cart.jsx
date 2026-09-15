// frontend/src/components/Cart.jsx
import { useState } from 'react';

export default function Cart({ items, total, onClose, onChangeQty, onCheckout }) {
  const [step, setStep] = useState('cart');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [comment, setComment] = useState('');

  const handleCheckout = () => {
    if (!address.trim() || !phone.trim()) {
      alert('Заполните адрес и телефон');
      return;
    }
    onCheckout({ address, phone, comment });
  };

  return (
    <div className="cart-overlay" onClick={onClose}>
      <div className="cart-panel" onClick={(e) => e.stopPropagation()}>
        <div className="cart-header">
          <h2>{step === 'cart' ? '🛒 Корзина' : '📋 Оформление'}</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        {step === 'cart' && (
          <>
            <div className="cart-items">
              {items.length === 0 && <p className="empty">Корзина пуста</p>}
              {items.map((item) => (
                <div key={item.menu_item.id} className="cart-item">
                  <img src={item.menu_item.image} alt={item.menu_item.name} />
                  <div className="cart-item-info">
                    <span className="cart-item-name">{item.menu_item.name}</span>
                    <span className="cart-item-price">{item.menu_item.price} ₽</span>
                  </div>
                  <div className="cart-item-qty">
                    <button onClick={() => onChangeQty(item.menu_item.id, -1)}>−</button>
                    <span>{item.quantity}</span>
                    <button onClick={() => onChangeQty(item.menu_item.id, 1)}>+</button>
                  </div>
                </div>
              ))}
            </div>
            {items.length > 0 && (
              <div className="cart-footer">
                <div className="cart-total">
                  <span>Итого:</span>
                  <span className="total-price">{total} ₽</span>
                </div>
                <button className="checkout-btn" onClick={() => setStep('checkout')}>
                  Оформить заказ
                </button>
              </div>
            )}
          </>
        )}

        {step === 'checkout' && (
          <div className="checkout-form">
            <input
              type="text"
              placeholder="Адрес доставки"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
            <input
              type="tel"
              placeholder="Телефон"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <textarea
              placeholder="Комментарий к заказу (необязательно)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
            />
            <button className="checkout-btn" onClick={handleCheckout}>
              Подтвердить заказ · {total} ₽
            </button>
            <button className="back-btn" onClick={() => setStep('cart')}>
              ← Назад в корзину
            </button>
          </div>
        )}
      </div>
    </div>
  );
}