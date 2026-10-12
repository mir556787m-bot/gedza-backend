// frontend/src/components/SupportSheet.jsx
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './SupportSheet.css';

const SUPPORT_PHONE = '+7 (347) 200 30 04';
const SUPPORT_PHONE_CLEAN = '+73472003004';

const SOCIALS = [
  {
    id: 'vk',
    label: 'ВКонтакте',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M13.162 18.994c.609 0 .858-.406.851-.915-.031-1.917.714-2.949 2.059-1.604 1.488 1.488 1.796 2.519 3.603 2.519h3.2c.808 0 1.126-.26 1.126-.668 0-.863-1.421-2.386-2.625-3.504-1.686-1.565-1.765-1.602-.313-3.486 1.801-2.339 4.157-5.336 2.073-5.336h-3.981c-.772 0-.828.435-1.103 1.083-.995 2.347-2.886 5.387-3.604 4.922-.751-.485-.407-2.406-.35-5.261.015-.754.011-1.271-1.141-1.539-.629-.145-1.241-.205-1.809-.205-2.273 0-3.841.953-2.95 1.119 1.571.293 1.42 3.692 1.054 5.16-.638 2.556-3.036-2.024-4.035-4.305-.241-.548-.315-.974-1.175-.974h-3.255c-.492 0-.787.16-.787.516 0 .602 2.96 6.72 5.786 9.77 2.756 2.975 5.48 2.708 7.376 2.708z"/>
      </svg>
    ),
  },
  {
    id: 'max',
    label: 'MAX',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
      </svg>
    ),
  },
  {
    id: 'telegram',
    label: 'Telegram',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/>
      </svg>
    ),
  },
];

export default function SupportSheet({ open, onClose }) {
  const { scrollRef } = useScrollPosition({ isEnabled: open });

  const handlePhoneClick = () => {
    window.location.href = `tel:${SUPPORT_PHONE_CLEAN}`;
  };

  const handleSocialClick = (socialId) => {
    const urls = {
      vk: 'https://vk.com/gedza',
      max: 'https://max.ru/gedza',
      telegram: 'https://t.me/gedza',
    };
    if (urls[socialId]) {
      window.open(urls[socialId], '_blank');
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
        <button className="support-close" onClick={onClose} aria-label="Закрыть">✕</button>
        <Sheet.Content
          scrollRef={scrollRef}
          scrollClassName="support-scroll"
        >
          <div className="support-sheet">
            <div className="support-icon-wrap">
              <div className="support-icon-bg" />
              <div className="support-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
                  <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
                </svg>
              </div>
            </div>

            <h2 className="support-title">Поддержка</h2>
            <p className="support-subtitle">
              У вас проблема с заказом или вопрос?<br />
              Обратитесь к нам!
            </p>

            <button className="support-phone-card" onClick={handlePhoneClick}>
              <div className="support-phone-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                </svg>
              </div>
              <span className="support-phone-number">{SUPPORT_PHONE}</span>
              <span className="support-phone-arrow">›</span>
            </button>

            <div className="support-divider">
              <span className="support-divider-text">или</span>
            </div>

            <div className="support-socials">
              {SOCIALS.map((social) => (
                <button
                  key={social.id}
                  className="support-social-btn"
                  onClick={() => handleSocialClick(social.id)}
                  aria-label={social.label}
                >
                  <span className="support-social-icon">{social.icon}</span>
                </button>
              ))}
            </div>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}