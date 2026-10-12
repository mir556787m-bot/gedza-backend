// frontend/src/components/AddressSheet.jsx
import { useState, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './AddressSheet.css';

const EMPTY_FORM = {
  street: '',
  flat: '',
  floor: '',
  entrance: '',
  door_code: '',
  comment: '',
  is_private: false,
};

export default function AddressSheet({
  open,
  addresses,
  onAdd,
  onSelect,
  onDelete,
  onClose,
}) {
  const [mode, setMode] = useState('list');
  const [form, setForm] = useState(EMPTY_FORM);

  const { scrollRef } = useScrollPosition({ isEnabled: open });

  useEffect(() => {
    if (!open) {
      setMode('list');
      setForm(EMPTY_FORM);
    }
  }, [open]);

  const handleSave = () => {
    if (!form.street.trim()) {
      alert('Введите адрес');
      return;
    }
    const details = {
      flat: form.flat,
      floor: form.floor,
      entrance: form.entrance,
      door_code: form.door_code,
      comment: form.comment,
      is_private: form.is_private,
    };
    onAdd(form.street, details);
    setForm(EMPTY_FORM);
    setMode('list');
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
          scrollClassName="as-scroll"
        >
          <div className="as-sheet">
            <div className="as-header">
              <h2 className="as-title">
                {mode === 'list' ? 'Мои адреса' : 'Новый адрес'}
              </h2>
              <button className="as-close" onClick={onClose} aria-label="Закрыть">✕</button>
            </div>

            {mode === 'list' ? (
              <>
                <button className="as-add-btn" onClick={() => setMode('form')}>
                  + Добавить адрес
                </button>
                <div className="as-list">
                  {addresses.length === 0 && (
                    <div className="as-empty">Нет сохранённых адресов</div>
                  )}
                  {addresses.map((addr) => (
                    <div key={addr.id} className="as-item">
                      <div className="as-item-info" onClick={() => onSelect(addr)}>
                        <svg
                          width="20"
                          height="20"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                          <circle cx="12" cy="10" r="3" />
                        </svg>
                        <div>
                          <div className="as-item-address">{addr.address}</div>
                          {addr.address_details && (
                            <div className="as-item-details">
                              {[
                                addr.address_details.flat && `кв. ${addr.address_details.flat}`,
                                addr.address_details.floor && `этаж ${addr.address_details.floor}`,
                                addr.address_details.entrance && `подъезд ${addr.address_details.entrance}`,
                              ]
                                .filter(Boolean)
                                .join(', ')}
                            </div>
                          )}
                        </div>
                      </div>
                      <button
                        className="as-item-del"
                        onClick={() => onDelete(addr.id)}
                        aria-label="Удалить"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="as-form">
                <input
                  type="text"
                  placeholder="Город, улица, дом"
                  value={form.street}
                  onChange={(e) => setForm({ ...form, street: e.target.value })}
                />
                <div className="as-form-row">
                  <input
                    type="text"
                    placeholder="Кв."
                    value={form.flat}
                    onChange={(e) => setForm({ ...form, flat: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="Этаж"
                    value={form.floor}
                    onChange={(e) => setForm({ ...form, floor: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="Подъезд"
                    value={form.entrance}
                    onChange={(e) => setForm({ ...form, entrance: e.target.value })}
                  />
                </div>
                <input
                  type="text"
                  placeholder="Код двери"
                  value={form.door_code}
                  onChange={(e) => setForm({ ...form, door_code: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="Комментарий курьеру"
                  value={form.comment}
                  onChange={(e) => setForm({ ...form, comment: e.target.value })}
                />
                <div className="as-form-check">
                  <input
                    type="checkbox"
                    id="is_private"
                    checked={form.is_private}
                    onChange={(e) => setForm({ ...form, is_private: e.target.checked })}
                  />
                  <label htmlFor="is_private">Частный дом</label>
                </div>
                <button className="as-save" onClick={handleSave}>
                  Сохранить адрес
                </button>
              </div>
            )}
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}