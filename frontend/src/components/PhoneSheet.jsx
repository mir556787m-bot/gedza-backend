// frontend/src/components/PhoneSheet.jsx
import { useState, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './PhoneSheet.css';

export default function PhoneSheet({ open, initialValue = '', onSave, onClose }) {
  const [phone, setPhone] = useState(initialValue || '');
  const { scrollRef } = useScrollPosition({ isEnabled: open });

  useEffect(() => {
    if (open) setPhone(initialValue || '');
  }, [open, initialValue]);

  const formatPhone = (value) => {
    const digits = value.replace(/\D/g, '').slice(0, 11);
    if (!digits) return '';
    let formatted = '+7';
    if (digits.length > 1) formatted += ' (' + digits.slice(1, 4);
    if (digits.length >= 5) formatted += ') ' + digits.slice(4, 7);
    if (digits.length >= 8) formatted += '-' + digits.slice(7, 9);
    if (digits.length >= 10) formatted += '-' + digits.slice(9, 11);
    return formatted;
  };

  const handleChange = (e) => {
    const digits = e.target.value.replace(/\D/g, '');
    setPhone(formatPhone(digits));
  };

  const handleSave = () => {
    const digits = phone.replace(/\D/g, '');
    if (digits.length < 11) {
      alert('Введите полный номер телефона');
      return;
    }
    onSave(phone);
  };

  return (
    <Sheet
      isOpen={open}
      onClose={onClose}
      detent="content"
      dragVelocityThreshold={500}
      dragCloseThreshold={0.25}
      tweenConfig={{ ease: 'easeOut', duration: 0.4 }}
    >
      <Sheet.Container>
        <Sheet.Header />
        <Sheet.Content
          scrollRef={scrollRef}
          scrollClassName="phs-scroll"
        >
          <div className="phs-sheet">
            <button className="phs-close" onClick={onClose} aria-label="Закрыть">✕</button>
            <h2 className="phs-title">Введите телефон</h2>
            <p className="phs-hint">
              На этот номер позвонит курьер для уточнения деталей заказа
            </p>
            <input
              className="phs-input"
              type="tel"
              placeholder="+7 (___) ___-__-__"
              value={phone}
              onChange={handleChange}
              autoFocus
            />
            <button
              className="phs-submit"
              onClick={handleSave}
              disabled={phone.replace(/\D/g, '').length < 11}
            >
              Сохранить
            </button>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}