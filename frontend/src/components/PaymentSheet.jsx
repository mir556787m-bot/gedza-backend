// frontend/src/components/PaymentSheet.jsx
import { useState, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './PaymentSheet.css';

const METHODS = [
  { id: 'cash', label: 'Наличными', subtitle: 'При получении' },
  { id: 'card_on_delivery', label: 'Картой при получении', subtitle: 'Курьеру' },
  { id: 'card_online', label: 'Картой онлайн', subtitle: 'Сейчас' },
];

export default function PaymentSheet({ open, selected, onSelect, onClose }) {
  const [local, setLocal] = useState(selected || null);
  const [saving, setSaving] = useState(false);

  const { scrollRef } = useScrollPosition({ isEnabled: open });

  useEffect(() => {
    if (open) {
      setLocal(selected || null);
      setSaving(false);
    }
  }, [open, selected]);

  const handlePick = (id) => {
    if (saving) return;
    setLocal(id);
  };

  const handleConfirm = async () => {
    if (saving || !local) return;
    setSaving(true);
    try {
      await onSelect(local);
    } catch (e) {
      console.error('PaymentSheet onSelect error:', e);
    } finally {
      setSaving(false);
      onClose();
    }
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
          scrollClassName="pms-scroll"
        >
          <div className="pms-sheet">
            <h2 className="pms-title">Способ оплаты</h2>
            <div className="pms-list">
              {METHODS.map((m) => (
                <button
                  key={m.id}
                  className={`pms-item ${local === m.id ? 'active' : ''}`}
                  onClick={() => handlePick(m.id)}
                  disabled={saving}
                >
                  <div className="pms-radio">
                    {local === m.id && <div className="pms-radio-dot" />}
                  </div>
                  <div className="pms-info">
                    <span className="pms-label">{m.label}</span>
                    <span className="pms-sub">{m.subtitle}</span>
                  </div>
                </button>
              ))}
            </div>

            <button
              className="pms-confirm"
              onClick={handleConfirm}
              disabled={saving || !local}
            >
              {saving ? 'Сохранение...' : 'Выбрать'}
            </button>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}