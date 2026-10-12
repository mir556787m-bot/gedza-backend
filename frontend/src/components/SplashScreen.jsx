// frontend/src/components/WheelBanner.jsx
import './WheelBanner.css';

export default function WheelBanner({ onClick }) {
  return (
    <div className="wheel-banner" onClick={onClick}>
      <div className="wheel-banner-icon">🎡</div>
      <span className="wheel-banner-text">Крути колесо и выиграй приз!</span>
      <span className="wheel-banner-arrow">›</span>
    </div>
  );
}