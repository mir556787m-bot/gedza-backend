// frontend/src/components/WheelModal.jsx
import { useState } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import { wheelSpin } from '../api';
import './WheelModal.css';

const PRIZES = ['Суши Пончик', 'Онигири', 'Удон с курицей', 'Суши торт', 'Фортуна сет'];

export default function WheelModal({ open, userId, onClose, onPrizeWon }) {
  const [spinning, setSpinning] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [prize, setPrize] = useState(null);
  const [canSpin, setCanSpin] = useState(true);

  const { scrollRef } = useScrollPosition({ isEnabled: open });

  const handleSpin = async () => {
    if (spinning || !canSpin) return;
    setSpinning(true);
    try {
      const result = await wheelSpin(userId);
      setRotation(result.angle);
      setTimeout(() => {
        setSpinning(false);
        setPrize(result.prize_name);
        setCanSpin(false);
        if (onPrizeWon) onPrizeWon(result);
      }, 4200);
    } catch (e) {
      setSpinning(false);
      if (e?.response?.status === 429) {
        setCanSpin(false);
        alert('Сегодня уже крутили — приходите завтра!');
      } else {
        alert('Ошибка колеса. Попробуйте позже.');
      }
    }
  };

  const sectorAngle = 360 / PRIZES.length;

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
        <button className="wm-close" onClick={onClose} aria-label="Закрыть">✕</button>
        <Sheet.Content
          scrollRef={scrollRef}
          scrollClassName="wm-scroll"
        >
          <div className="wm-sheet">
            <h2 className="wm-title">Раскрути колесо</h2>
            <p className="wm-subtitle">И получишь подарок!</p>
            <div className="wm-wheel-wrap">
              <div
                className="wm-wheel"
                style={{
                  transform: `rotate(${rotation}deg)`,
                  transition: spinning
                    ? 'transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99)'
                    : 'none',
                }}
              >
                {PRIZES.map((name, i) => (
                  <div
                    key={i}
                    className="wm-sector"
                    style={{
                      transform: `rotate(${i * sectorAngle}deg)`,
                      background: i % 2 === 0 ? '#ffffff' : '#e8e6f5',
                    }}
                  >
                    <span className="wm-sector-text">{name}</span>
                  </div>
                ))}
                <div className="wm-center-cap" />
              </div>
              <div className="wm-pointer" />
            </div>
            {prize && (
              <div className="wm-prize">
                🎉 Ваш приз: <strong>{prize}</strong>
              </div>
            )}
            <button
              className="wm-spin-btn"
              onClick={handleSpin}
              disabled={spinning || !canSpin}
            >
              {spinning ? 'Крутим...' : prize ? 'Забрать!' : 'Раскрутить'}
            </button>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}