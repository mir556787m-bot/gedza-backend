// frontend/src/components/OrderStatusSheet.jsx
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './OrderStatusSheet.css';

const STATUS_STEPS = [
  { key: 'pending', icon: 'clock', label: 'Ожидаем подтверждения' },
  { key: 'cooking', icon: 'chef', label: 'Готовится' },
  { key: 'delivering', icon: 'box', label: 'В доставке' },
  { key: 'delivered', icon: 'check', label: 'Доставлен' },
];

const STATUS_LABELS = {
  pending: { text: 'В ОЖИДАНИИ', color: 'blue' },
  confirmed: { text: 'ПОДТВЕРЖДЁН', color: 'orange' },
  cooking: { text: 'ГОТОВИТСЯ', color: 'orange' },
  delivering: { text: 'В ДОСТАВКЕ', color: 'purple' },
  delivered: { text: 'ДОСТАВЛЕН', color: 'green' },
  cancelled: { text: 'ОТМЕНЁН', color: 'gray' },
  completed: { text: 'ЗАВЕРШЁН', color: 'green' },
};

export default function OrderStatusSheet({ open, order, onClose, onRepeat }) {
  const { scrollRef } = useScrollPosition({ isEnabled: open });

  if (!order) return null;

  const statusInfo = STATUS_LABELS[order.status] || STATUS_LABELS.pending;
  const currentStepIndex = STATUS_STEPS.findIndex((s) => s.key === order.status);
  const isCancelled = order.status === 'cancelled';

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
          scrollRef={scrollRef}
          scrollClassName="order-status-scroll"
        >
          <div className="order-status-sheet">

            {/* ═══ Заголовок ═══ */}
            <div className="order-status-header">
              <h2 className="order-status-title">Заказ #{order.id}</h2>
              <span className={`order-status-badge ${statusInfo.color}`}>
                {statusInfo.text}
              </span>
            </div>

            {/* ═══ Прогресс ═══ */}
            {!isCancelled && (
              <div className="order-progress">
                {STATUS_STEPS.map((step, i) => {
                  const isActive = i <= currentStepIndex;
                  const isCurrent = i === currentStepIndex;
                  return (
                    <div key={step.key} className="order-progress-step">
                      <div className={`order-progress-icon ${isActive ? 'active' : ''} ${isCurrent ? 'current' : ''}`}>
                        {step.icon === 'clock' && <ClockIcon />}
                        {step.icon === 'chef' && <ChefIcon />}
                        {step.icon === 'box' && <BoxIcon />}
                        {step.icon === 'check' && <CheckIcon />}
                      </div>
                      {i < STATUS_STEPS.length - 1 && (
                        <div className={`order-progress-line ${isActive ? 'active' : ''}`} />
                      )}
                    </div>
                  );
                })}
                <div className="order-progress-label">
                  {STATUS_STEPS[currentStepIndex]?.label || 'Ожидаем подтверждения'}
                </div>
              </div>
            )}

            {/* ═══ Отменён ═══ */}
            {isCancelled && (
              <div className="order-cancelled">
                <div className="order-cancelled-icon">✕</div>
                <div className="order-cancelled-text">Заказ отменён</div>
              </div>
            )}

            {/* ═══ Товары ═══ */}
            <div className="order-items">
              {order.items?.map((item) => (
                <div key={item.id} className="order-item">
                  <img src={item.image} alt={item.name} className="order-item-img" />
                  <div className="order-item-info">
                    <span className="order-item-name">{item.name}</span>
                    {item.mass && <span className="order-item-mass">{item.mass}</span>}
                  </div>
                  <span className="order-item-price">{item.price} ₽</span>
                </div>
              ))}
            </div>

            {/* ═══ Детали ═══ */}
            <div className="order-details">
              <DetailRow label="Заказ создан" value={order.createdAt} />
              <DetailRow label="Сумма" value={`${order.total} ₽`} />
              {order.appliedPromos?.length > 0 && (
                <DetailRow label="Примененные акции" value={order.appliedPromos.join(', ')} />
              )}
              {order.bonusEarned > 0 && (
                <DetailRow label="Получено баллов" value={order.bonusEarned} />
              )}
              <DetailRow
                label="Способ получения заказа"
                value={order.deliveryType === 'pickup' ? 'Самовывоз' : 'Доставка'}
              />
              <DetailRow label="Адрес" value={order.address} />
              <DetailRow label="Ко времени" value={order.deliveryTime} />
              <DetailRow label="Способ оплаты" value={order.paymentMethod} />
            </div>

            {/* ═══ Кнопки ═══ */}
            <div className="order-actions">
              <button className="order-btn-primary" onClick={() => onRepeat?.(order)}>
                Повторить заказ
              </button>
              <button className="order-btn-secondary" onClick={onClose}>
                Поддержка
              </button>
            </div>

          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="order-detail-row">
      <span className="order-detail-label">{label}</span>
      <span className="order-detail-value">{value}</span>
    </div>
  );
}

function ClockIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function ChefIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 13.87A4 4 0 0 1 7.41 6a5.11 5.11 0 0 1 1.05-1.54 5 5 0 0 1 7.08 0A5.11 5.11 0 0 1 16.59 6 4 4 0 0 1 18 13.87V21H6Z" />
      <line x1="6" y1="17" x2="18" y2="17" />
    </svg>
  );
}

function BoxIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}