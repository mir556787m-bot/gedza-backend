// frontend/src/components/DetailsSheet.jsx
import { useState, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './DetailsSheet.css';

export default function DetailsSheet({ open, initial = {}, onSave, onClose }) {
  const [form, setForm] = useState({
    flat: '',
    entrance: '',
    floor: '',
    door_code: '',
    comment: '',
    is_private: false,
  });

  const { scrollRef, scrollPosition } = useScrollPosition({
    isEnabled: open,
  });

  useEffect(() => {
    if (open) {
      setForm({
        flat: initial.flat || '',
        entrance: initial.entrance || '',
        floor: initial.floor || '',
        door_code: initial.door_code || '',
        comment: initial.comment || '',
        is_private: !!initial.is_private,
      });
    }
  }, [open, initial]);

  const handleSave = () => {
    onSave(form);
    onClose();
  };

  return (
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
            className="ds-scroll"
            style={{ overflowY: 'auto', height: '100%' }}
          >
            <div className="ds-sheet">
              <div className="ds-header">
                <button className="ds-back" onClick={onClose} aria-label="Назад">‹</button>
                <h2 className="ds-title">Заполните детали</h2>
              </div>

              <div className="ds-form">
                <div className="ds-form-row">
                  <input
                    type="text"
                    placeholder="Квартира"
                    value={form.flat}
                    onChange={(e) => setForm({ ...form, flat: e.target.value })}
                    disabled={form.is_private}
                  />
                  <input
                    type="text"
                    placeholder="Подъезд"
                    value={form.entrance}
                    onChange={(e) => setForm({ ...form, entrance: e.target.value })}
                    disabled={form.is_private}
                  />
                </div>
                <div className="ds-form-row">
                  <input
                    type="text"
                    placeholder="Этаж"
                    value={form.floor}
                    onChange={(e) => setForm({ ...form, floor: e.target.value })}
                    disabled={form.is_private}
                  />
                  <input
                    type="text"
                    placeholder="Код двери"
                    value={form.door_code}
                    onChange={(e) => setForm({ ...form, door_code: e.target.value })}
                    disabled={form.is_private}
                  />
                </div>
                <textarea
                  className="ds-textarea"
                  placeholder="Комментарий"
                  value={form.comment}
                  onChange={(e) => setForm({ ...form, comment: e.target.value })}
                  rows={3}
                />
                <label className="ds-checkbox">
                  <input
                    type="checkbox"
                    checked={form.is_private}
                    onChange={(e) => setForm({ ...form, is_private: e.target.checked })}
                  />
                  <span>Частный дом</span>
                </label>
              </div>

              <button className="ds-submit" onClick={handleSave}>
                Добавить
              </button>
            </div>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}