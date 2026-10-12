// frontend/src/components/RegisterSheet.jsx
import { useState, useEffect, useRef } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import DetailsSheet from './DetailsSheet';
import PrivacyPolicy from './PrivacyPolicy';
import './RegisterSheet.css';

export default function RegisterSheet({ open, initialPhone = '', onSave, onClose }) {
  const [name, setName] = useState('');
  const [nameEditing, setNameEditing] = useState(false);
  const [phone, setPhone] = useState(initialPhone || '');
  const [address, setAddress] = useState('');
  const [addressDetails, setAddressDetails] = useState({});
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [legalAgreed, setLegalAgreed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [contactLoading, setContactLoading] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);

  const [focusedField, setFocusedField] = useState(null);

  const addressRef = useRef(null);
  const nameRef = useRef(null);
  const phoneRef = useRef(null);

  const { scrollRef, scrollPosition } = useScrollPosition({
    isEnabled: open,
  });

  const hasRequestContact =
    typeof window !== 'undefined' &&
    window.WebApp &&
    typeof window.WebApp.requestContact === 'function';

  const isHouseNumberMissing = () => {
    if (!address) return false;
    return /,\s*дом\s*$/.test(address);
  };

  useEffect(() => {
    if (!open) return;
    setPhone(initialPhone || '');
    setAddress('');
    setAddressDetails({});
    setLegalAgreed(false);
    setNameEditing(false);
    setFocusedField(null);

    if (window.WebApp?.initDataUnsafe?.user) {
      const u = window.WebApp.initDataUnsafe.user;
      const full = [u.first_name, u.last_name].filter(Boolean).join(' ').trim();
      if (full) setName(full);
    }
  }, [open, initialPhone]);

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

  const handlePhoneChange = (e) => {
    setPhone(formatPhone(e.target.value.replace(/\D/g, '')));
  };

  const handleRequestContact = async () => {
    if (!hasRequestContact) {
      alert('Функция недоступна. Введите номер вручную.');
      return;
    }
    setContactLoading(true);
    try {
      const result = await window.WebApp.requestContact();
      if (result?.phone) {
        setPhone(formatPhone('+' + result.phone));
      } else {
        alert('MAX не вернул номер. Введите вручную.');
      }
    } catch (err) {
      console.warn('requestContact error:', err);
      alert('Не удалось получить номер. Введите вручную.');
    } finally {
      setContactLoading(false);
    }
  };

  const handleAddressFocus = () => {
    setFocusedField('address');
    if (!address.trim()) {
      setAddress('Уфа, ');
      setTimeout(() => {
        const el = addressRef.current;
        if (el) el.setSelectionRange(el.value.length, el.value.length);
      }, 0);
    }
  };

  const handleAddressChange = (e) => {
    let val = e.target.value;

    if (val.startsWith('Уфа, ')) {
      const afterCity = val.slice(5);
      const hasHouse = /,\s*дом/i.test(val);

      if (!hasHouse && afterCity.includes(',')) {
        const commaIdx = afterCity.indexOf(',');
        const streetName = afterCity.slice(0, commaIdx).trim();
        if (streetName.length >= 1) {
          val = `Уфа, ${streetName}, дом `;
        }
      }
    }

    setAddress(val);
    setTimeout(() => {
      const el = addressRef.current;
      if (el) el.setSelectionRange(el.value.length, el.value.length);
    }, 0);
  };

  const clearField = (setter, ref, field) => {
    setter('');
    setTimeout(() => {
      const el = ref.current;
      if (el) el.focus();
      setFocusedField(field);
    }, 0);
  };

  const detailsSummary = () => {
    const parts = [];
    if (addressDetails.flat) parts.push(`кв. ${addressDetails.flat}`);
    if (addressDetails.entrance) parts.push(`подъезд ${addressDetails.entrance}`);
    if (addressDetails.floor) parts.push(`этаж ${addressDetails.floor}`);
    if (addressDetails.door_code) parts.push(`домофон ${addressDetails.door_code}`);
    if (addressDetails.is_private) parts.unshift('Частный дом');
    return parts.join(', ');
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        phone,
        address: address.trim(),
        address_details: addressDetails,
        legal_agreed: legalAgreed,
      });
    } catch (e) {
      console.error('registerUser error:', e);
    } finally {
      setSaving(false);
    }
  };

  const canContinue =
    name.trim().length >= 2 &&
    phone.replace(/\D/g, '').length === 11 &&
    address.trim().length >= 5 &&
    !isHouseNumberMissing() &&
    legalAgreed;

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
          <Sheet.Content
            disableScroll
            disableDrag={scrollPosition !== 'top'}
          >
            <div
              ref={scrollRef}
              className="rs-scroll"
              style={{ overflowY: 'auto', height: '100%' }}
            >
              <div className="rs-sheet">
                <h2 className="rs-title">Профиль</h2>
                <p className="rs-subtitle">
                  Для оформления заказа нам нужны ваши данные
                </p>

                {/* ─── Имя ─── */}
                <label className="rs-label">Имя</label>
                <div className="rs-name-wrap">
                  <input
                    ref={nameRef}
                    className="rs-input rs-input-with-clear"
                    type="text"
                    placeholder="Ваше имя"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    readOnly={!nameEditing}
                    onFocus={() => setFocusedField('name')}
                    onBlur={() => setFocusedField(null)}
                  />
                  {nameEditing && name && focusedField === 'name' && (
                    <button
                      type="button"
                      className="rs-clear-btn rs-clear-name"
                      onClick={() => clearField(setName, nameRef, 'name')}
                      aria-label="Очистить"
                    >
                      ✕
                    </button>
                  )}
                  <button
                    type="button"
                    className="rs-name-edit"
                    onClick={() => setNameEditing(!nameEditing)}
                    aria-label="Редактировать имя"
                  >
                    {nameEditing ? '✓' : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                    )}
                  </button>
                </div>

                {/* ─── Телефон ─── */}
                <label className="rs-label">Телефон</label>
                <div className="rs-phone-wrap">
                  <input
                    ref={phoneRef}
                    className="rs-input rs-input-with-clear"
                    type="tel"
                    placeholder="+7 (___) ___-__-__"
                    value={phone}
                    onChange={handlePhoneChange}
                    onFocus={() => setFocusedField('phone')}
                    onBlur={() => setFocusedField(null)}
                  />
                  {phone && focusedField === 'phone' && (
                    <button
                      type="button"
                      className="rs-clear-btn rs-clear-phone"
                      onClick={() => clearField(setPhone, phoneRef, 'phone')}
                      aria-label="Очистить"
                    >
                      ✕
                    </button>
                  )}
                  {hasRequestContact && !phone && (
                    <button
                      className="rs-phone-btn"
                      onClick={handleRequestContact}
                      type="button"
                      disabled={contactLoading}
                    >
                      {contactLoading ? '…' : 'Из MAX'}
                    </button>
                  )}
                </div>

                {/* ─── Адрес ─── */}
                <label className="rs-label">Адрес</label>
                <div className="rs-input-wrap">
                  <input
                    ref={addressRef}
                    className={`rs-input rs-input-with-clear ${isHouseNumberMissing() ? 'rs-input-error' : ''}`}
                    type="text"
                    placeholder="Уфа, улица, дом"
                    value={address}
                    onChange={handleAddressChange}
                    onFocus={handleAddressFocus}
                    onBlur={() => setFocusedField(null)}
                  />
                  {address && focusedField === 'address' && (
                    <button
                      type="button"
                      className="rs-clear-btn"
                      onClick={() => clearField(setAddress, addressRef, 'address')}
                      aria-label="Очистить"
                    >
                      ✕
                    </button>
                  )}
                </div>
                {isHouseNumberMissing() && (
                  <div className="rs-hint">Укажите номер дома</div>
                )}
                <input
                  className="rs-input rs-input-readonly"
                  placeholder="Подъезд, этаж, квартира"
                  value={detailsSummary()}
                  readOnly
                  onClick={() => setDetailsOpen(true)}
                />

                {/* ─── Согласие ─── */}
                <label className="rs-legal">
                  <input
                    type="checkbox"
                    checked={legalAgreed}
                    onChange={(e) => setLegalAgreed(e.target.checked)}
                  />
                  <span>
                    Я ознакомлен(а) с{' '}
                    <button
                      type="button"
                      className="rs-link-btn"
                      onClick={(e) => {
                        e.preventDefault();
                        setPrivacyOpen(true);
                      }}
                    >
                      политикой конфиденциальности
                    </button>{' '}
                    и даю согласие на обработку персональных данных
                  </span>
                </label>

                <button
                  className="rs-submit"
                  onClick={handleSave}
                  disabled={!canContinue || saving}
                >
                  {saving ? 'Сохранение...' : 'Продолжить'}
                </button>
              </div>
            </div>
          </Sheet.Content>
        </Sheet.Container>
        <Sheet.Backdrop />
      </Sheet>

      <DetailsSheet
        open={detailsOpen}
        initial={addressDetails}
        onSave={(data) => setAddressDetails(data)}
        onClose={() => setDetailsOpen(false)}
      />

      <PrivacyPolicy
        open={privacyOpen}
        onClose={() => setPrivacyOpen(false)}
      />
    </>
  );
}