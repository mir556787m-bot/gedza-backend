// frontend/src/components/LocationSheet.jsx
import { useState, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import { getRestaurants, getAddresses, initSession, addAddress, deleteAddress } from '../api';
import DetailsSheet from './DetailsSheet';
import './LocationSheet.css';

export default function LocationSheet({ userId, onConfirm, onClose, currentType = 'delivery', open }) {
  const [mode, setMode] = useState(currentType || 'delivery');
  const [step, setStep] = useState('list');
  const [restaurants, setRestaurants] = useState([]);
  const [selectedRestId, setSelectedRestId] = useState(null);
  const [addresses, setAddresses] = useState([]);
  const [selectedAddrId, setSelectedAddrId] = useState(null);
  const [newAddress, setNewAddress] = useState('');
  const [newAddressDetails, setNewAddressDetails] = useState({});
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const { scrollRef, scrollPosition } = useScrollPosition({
    isEnabled: open,
  });

  // диагностика — можно убрать после проверки
  useEffect(() => {
    if (open) console.log('[LS] scrollPosition =', scrollPosition);
  }, [open, scrollPosition]);

  useEffect(() => {
    if (!open) {
      setSelectedRestId(null);
      setSelectedAddrId(null);
      setNewAddress('');
      setNewAddressDetails({});
      setMode(currentType || 'delivery');
      setStep('list');
      return;
    }
    loadAll();
  }, [open, userId, currentType]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [r, a] = await Promise.all([
        getRestaurants().catch(() => []),
        getAddresses(userId).catch(() => ({ addresses: [] })),
      ]);
      setRestaurants(Array.isArray(r) ? r : []);
      setAddresses(a?.addresses || []);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode) => {
    if (newMode === mode) return;
    setMode(newMode);
    setStep('list');
    setNewAddressDetails({});
    setNewAddress('');
    if (newMode === 'pickup') setSelectedAddrId(null);
    else setSelectedRestId(null);
  };

  const selectedRestaurant = restaurants.find((x) => x.id === selectedRestId);

  const detailsSummary = () => {
    const parts = [];
    if (newAddressDetails.flat) parts.push(`кв. ${newAddressDetails.flat}`);
    if (newAddressDetails.floor) parts.push(`этаж ${newAddressDetails.floor}`);
    if (newAddressDetails.entrance) parts.push(`подъезд ${newAddressDetails.entrance}`);
    if (newAddressDetails.door_code) parts.push(`домофон ${newAddressDetails.door_code}`);
    if (newAddressDetails.is_private) parts.unshift('Частный дом');
    return parts.join(', ');
  };

  const isHouseNumberMissing = () => {
    if (!newAddress) return false;
    return /,\s*дом\s*$/.test(newAddress);
  };

  const handleSaveNewAddress = async () => {
    if (!newAddress.trim() || isHouseNumberMissing()) return;
    setSaving(true);
    try {
      await addAddress(userId, newAddress.trim(), newAddressDetails, addresses.length === 0);
      await initSession(userId, 'delivery', newAddress.trim(), newAddressDetails);
      onConfirm({
        delivery_type: 'delivery',
        address: newAddress.trim(),
        address_details: newAddressDetails,
        delivery_minutes: 90,
      });
    } catch (e) {
      console.warn('save new address failed:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmDelivery = async () => {
    if (!selectedAddrId) return;
    const a = addresses.find((x) => x.id === selectedAddrId);
    if (!a) return;
    setSaving(true);
    try {
      await initSession(userId, 'delivery', a.address, a.address_details);
    } catch (e) {
      console.warn('initSession failed:', e);
    } finally {
      setSaving(false);
    }
    onConfirm({
      delivery_type: 'delivery',
      address: a.address,
      address_details: a.address_details,
      delivery_minutes: 90,
    });
  };

  const handleDeleteAddress = async (e, addrId) => {
    e.stopPropagation();
    e.preventDefault();
    if (!window.confirm('Удалить адрес?')) return;
    try {
      await deleteAddress(userId, addrId);
      setAddresses((prev) => prev.filter((a) => a.id !== addrId));
      if (selectedAddrId === addrId) setSelectedAddrId(null);
    } catch (err) {
      console.error('Ошибка удаления адреса:', err);
    }
  };

  const handleContinue = () => {
    if (mode === 'pickup') {
      if (!selectedRestId) return;
      setStep('detail');
    } else {
      handleConfirmDelivery();
    }
  };

  const handleConfirmPickup = async () => {
    if (!selectedRestaurant) return;
    setSaving(true);
    const minutes = selectedRestaurant.delivery_minutes || 30;
    try {
      await initSession(userId, 'pickup', selectedRestaurant.name, {
        restaurant_id: selectedRestaurant.id,
        restaurant_address: selectedRestaurant.address,
      });
    } catch (e) {
      console.warn('initSession failed:', e);
    } finally {
      setSaving(false);
    }
    onConfirm({
      delivery_type: 'pickup',
      restaurant_id: selectedRestaurant.id,
      address: selectedRestaurant.name,
      address_full: selectedRestaurant.address,
      delivery_minutes: minutes,
    });
  };

  const canContinue = mode === 'pickup' ? !!selectedRestId : !!selectedAddrId;
  const canSaveAddress = newAddress.trim().length >= 5 && !isHouseNumberMissing();

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
            scrollRef={scrollRef}
            scrollClassName="ls-scroll"
          >
            <div className="ls-sheet">
              {step === 'list' && (
                <div className="ls-tabs">
                  <div className={`ls-tabs-slider ${mode === 'pickup' ? 'right' : 'left'}`} />
                  <button
                    className={`ls-tab ${mode === 'delivery' ? 'active' : ''}`}
                    onClick={() => switchMode('delivery')}
                  >
                    <span>Доставка</span>
                    <svg width="22" height="22" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="72" cy="77" r="6" fill="currentColor" stroke="none" />
                      <circle cx="38" cy="77" r="6" fill="currentColor" stroke="none" />
                      <path d="M 72,40 L 72,72 L 38,72" />
                      <circle cx="58" cy="24" r="7" fill="currentColor" stroke="none" />
                      <path d="M 58,30 L 48,48 L 60,62 L 56,72" />
                      <path d="M 55,34 L 65,42 L 72,42" />
                    </svg>
                  </button>
                  <button
                    className={`ls-tab ${mode === 'pickup' ? 'active' : ''}`}
                    onClick={() => switchMode('pickup')}
                  >
                    <span>Самовывоз</span>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 2v7c0 1.1.9 2 2 2h1a2 2 0 0 0 2-2V2" />
                      <path d="M7 2v20" />
                      <path d="M19 2c-1.5 0-3 2-3 5v4c0 1.1.9 2 2 2h1v9" />
                    </svg>
                  </button>
                </div>
              )}

              {loading && <div className="ls-loading">Загрузка...</div>}

              {!loading && step === 'new-address' && mode === 'delivery' && (
                <>
                  <div className="ls-newaddr-header">
                    <button className="ls-back" onClick={() => setStep('list')} aria-label="Назад">‹</button>
                    <h2 className="ls-title">Новый адрес</h2>
                  </div>
                  <div className="ls-input-wrap">
                    <input
                      className={`ls-input ls-input-with-clear ${isHouseNumberMissing() ? 'ls-input-error' : ''}`}
                      type="text"
                      placeholder="Уфа, улица, дом"
                      value={newAddress}
                      onChange={(e) => setNewAddress(e.target.value)}
                      autoFocus
                    />
                    {newAddress && (
                      <button
                        type="button"
                        className="ls-clear-btn"
                        onClick={() => setNewAddress('')}
                        aria-label="Очистить"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                  {isHouseNumberMissing() && (
                    <div className="ls-hint">Укажите номер дома</div>
                  )}
                  <input
                    className="ls-input ls-input-readonly"
                    placeholder="Подъезд, этаж, квартира"
                    value={detailsSummary()}
                    readOnly
                    onClick={() => setDetailsOpen(true)}
                  />
                  <button
                    className="ls-submit"
                    disabled={!canSaveAddress || saving}
                    onClick={handleSaveNewAddress}
                  >
                    {saving ? 'Сохранение...' : 'Продолжить'}
                  </button>
                </>
              )}

              {!loading && mode === 'pickup' && step === 'detail' && selectedRestaurant && (
                <div className="ls-detail">
                  <h2 className="ls-title">{selectedRestaurant.name}</h2>
                  <p className="ls-detail-address">{selectedRestaurant.address}</p>
                  <p className="ls-detail-schedule">
                    {selectedRestaurant.schedule || 'Понедельник-Воскресенье 10:00-22:30'}
                  </p>
                  {selectedRestaurant.phone && (
                    <a className="ls-detail-phone" href={`tel:${selectedRestaurant.phone.replace(/[^\d+]/g, '')}`}>
                      {selectedRestaurant.phone}
                    </a>
                  )}
                  <div className="ls-detail-actions">
                    <button className="ls-btn-cancel" onClick={() => setStep('list')}>Отмена</button>
                    <button className="ls-btn-continue" onClick={handleConfirmPickup} disabled={saving}>
                      {saving ? 'Сохранение...' : 'Продолжить'}
                    </button>
                  </div>
                </div>
              )}

              {!loading && step === 'list' && (
                <>
                  {mode === 'delivery' && (
                    <div className="ls-body">
                      <div className="ls-body-header">
                        <div className="ls-title">Мои адреса</div>
                        <button
                          className="ls-add-address"
                          onClick={() => {
                            setNewAddress('');
                            setNewAddressDetails({});
                            setStep('new-address');
                          }}
                        >
                          + Добавить адрес
                        </button>
                      </div>
                      {addresses.length === 0 && (
                        <div className="ls-empty">Сохранённых адресов нет</div>
                      )}
                      {addresses.map((a) => (
                        <div
                          key={a.id}
                          className={`ls-radio-row ${selectedAddrId === a.id ? 'active' : ''}`}
                          onClick={() => setSelectedAddrId(a.id)}
                        >
                          <span className="ls-radio-dot" />
                          <div className="ls-radio-info">
                            <span className="ls-radio-name">{a.address}</span>
                            {a.address_details && (
                              <span className="ls-radio-details">
                                {[
                                  a.address_details.flat && `кв. ${a.address_details.flat}`,
                                  a.address_details.entrance && `подъезд ${a.address_details.entrance}`,
                                  a.address_details.floor && `этаж ${a.address_details.floor}`,
                                  a.address_details.door_code && `домофон ${a.address_details.door_code}`,
                                  a.address_details.comment,
                                  a.address_details.is_private && 'Частный дом',
                                ].filter(Boolean).join(', ')}
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            className="ls-addr-del"
                            onClick={(e) => handleDeleteAddress(e, a.id)}
                            aria-label="Удалить адрес"
                          >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M3 6h18" />
                              <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                              <path d="M10 11v6" /><path d="M14 11v6" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {mode === 'pickup' && (
                    <div className="ls-body">
                      <div className="ls-title">Самовывоз</div>
                      {restaurants.length === 0 && (
                        <div className="ls-empty">Рестораны не загружены</div>
                      )}
                      {restaurants.map((r) => (
                        <div
                          key={r.id}
                          className={`ls-radio-row ${selectedRestId === r.id ? 'active' : ''}`}
                          onClick={() => setSelectedRestId(r.id)}
                        >
                          <span className="ls-radio-dot" />
                          <div className="ls-radio-info">
                            <span className="ls-radio-name">{r.name}</span>
                            <span className="ls-radio-details">
                              {r.schedule || 'Понедельник-Воскресенье 10:00-22:30'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    className="ls-submit"
                    disabled={!canContinue || saving}
                    onClick={handleContinue}
                  >
                    {saving ? 'Сохранение...' : 'Продолжить'}
                  </button>
                </>
              )}
            </div>
          </Sheet.Content>
        </Sheet.Container>
        <Sheet.Backdrop />
      </Sheet>

      {detailsOpen && (
        <DetailsSheet
          open={detailsOpen}
          initial={newAddressDetails}
          onSave={(data) => setNewAddressDetails(data)}
          onClose={() => setDetailsOpen(false)}
        />
      )}
    </>
  );
}