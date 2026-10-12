// frontend/src/components/ConditionsSheet.jsx
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './ConditionsSheet.css';

export default function ConditionsSheet({ type = 'delivery', title, open, onClose }) {
  const { scrollRef } = useScrollPosition({ isEnabled: open });

  const CONDITIONS_DELIVERY = [
    { label: 'Минимальный заказ', value: '100 ₽' },
    { label: 'Время ожидания', value: '~ 90 мин' },
    { label: 'Доставка при заказе от 100 ₽', value: '150 ₽' },
    { label: 'Доставка при заказе от 4000 ₽', value: 'Бесплатно' },
  ];

  const CONDITIONS_PICKUP = [
    { label: 'Минимальный заказ', value: '0 ₽' },
    { label: 'Время ожидания', value: '~ 30 мин' },
  ];

  const rows = type === 'pickup' ? CONDITIONS_PICKUP : CONDITIONS_DELIVERY;

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
        <button className="cs-close-inline" onClick={onClose} aria-label="Закрыть">✕</button>
        <Sheet.Content
          scrollRef={scrollRef}
          scrollClassName="cs-scroll"
        >
          <div className="cs-sheet">
            <h2 className="cs-title">{title || 'Условия'}</h2>

            <div className="cs-conditions">
              {rows.map((c, i) => (
                <div key={i} className="cs-row">
                  <span className="cs-label">{c.label}</span>
                  <span className="cs-dots" />
                  <span className="cs-value">{c.value}</span>
                </div>
              ))}
            </div>

            <button className="cs-btn" onClick={onClose}>Закрыть</button>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}