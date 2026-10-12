// frontend/src/components/PromoTicket.jsx
import './PromoTicket.css';

export default function PromoTicket({
  promo,
  selected,
  onClick,
  disabled = false,
}) {
  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;

    try {
      window.WebApp?.HapticFeedback?.impactOccurred?.('light');
    } catch (_) {}

    onClick?.();
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick(e);
    }
  };

  const rawTitle = promo.title || promo.promocode || 'Промокод';
  let line1 = rawTitle;
  let line2 = '';
  const dashIdx = rawTitle.indexOf('—');
  if (dashIdx > 0) {
    const after = rawTitle.slice(dashIdx + 1).trim();
    const afterParts = after.split(' ');
    line1 = rawTitle.slice(0, dashIdx + 1).trim() + ' ' + afterParts[0];
    line2 = afterParts.slice(1).join(' ');
  }

  return (
    <div
      className={`promo-ticket ${selected ? 'selected' : ''} ${
        disabled ? 'disabled' : ''
      }`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKey}
      style={{ WebkitTapHighlightColor: 'transparent' }}
    >
      <svg
        className="promo-ticket-graphics"
        viewBox="0 0 280 130"
        preserveAspectRatio="none"
      >
        <g>
          {/* Белая подложка — R вогнутости 10 */}
          <path
            className="promo-ticket-base"
            d="M 14,0
               L 266,0
               A 14,14 0 0,1 280,14
               L 280,55
               A 10,10 0 0,0 280,75
               L 280,116
               A 14,14 0 0,1 266,130
               L 14,130
               A 14,14 0 0,1 0,116
               L 0,75
               A 10,10 0 0,0 0,55
               L 0,14
               A 14,14 0 0,1 14,0 Z"
          />
          {/* Пунктир — концентричные дуги (R=18), зазор 8px */}
          <path
            className="promo-ticket-dashed"
            d="M 14,8
               L 266,8
               A 6,6 0 0,1 272,14
               L 272,48.88
               A 18,18 0 0,0 272,81.12
               L 272,116
               A 6,6 0 0,1 266,122
               L 14,122
               A 6,6 0 0,1 8,116
               L 8,81.12
               A 18,18 0 0,0 8,48.88
               L 8,14
               A 6,6 0 0,1 14,8 Z"
          />
        </g>
      </svg>

      <div className="promo-ticket-content">
        <div className="promo-ticket-radio" />
        <div className="promo-ticket-info">
          <p className="promo-ticket-text">
            {line1}
            {line2 && <><br />{line2}</>}
          </p>
          {promo.tag && <span className="promo-ticket-tag">{promo.tag}</span>}
        </div>
      </div>
    </div>
  );
}