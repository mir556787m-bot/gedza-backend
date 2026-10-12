// frontend/src/components/PreorderSheet.jsx
import { useState, useMemo, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './PreorderSheet.css';

const WEEKDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
const MONTHS = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

const TIME_SLOTS = [
  '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00',
  '15:30', '16:00', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30',
  '21:00', '21:30', '22:00',
];

const MIN_PREORDER_DELAY_MIN = 120;

export default function PreorderSheet({ open, onSelect, onClose }) {
  const { scrollRef } = useScrollPosition({ isEnabled: open });

  const days = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Array.from({ length: 20 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      return d;
    });
  }, []);

  const [selectedDay, setSelectedDay] = useState(days[0]);
  const [selectedTime, setSelectedTime] = useState(null);

  useEffect(() => {
    if (!open) return;

    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const lastSlot = TIME_SLOTS[TIME_SLOTS.length - 1].split(':').map(Number);
    const lastSlotMinutes = lastSlot[0] * 60 + lastSlot[1];

    if (nowMinutes + MIN_PREORDER_DELAY_MIN > lastSlotMinutes) {
      setSelectedDay(days[1]);
    } else {
      setSelectedDay(days[0]);
    }
    setSelectedTime(null);
  }, [open, days]);

  const availableSlots = useMemo(() => {
    const today = new Date();
    const isToday = selectedDay.toDateString() === today.toDateString();
    if (!isToday) return TIME_SLOTS;

    const nowMinutes = today.getHours() * 60 + today.getMinutes();
    return TIME_SLOTS.filter((t) => {
      const [h, m] = t.split(':').map(Number);
      return h * 60 + m > nowMinutes + MIN_PREORDER_DELAY_MIN;
    });
  }, [selectedDay]);

  const isAsap = !selectedTime;

  const handleAsap = () => {
    onSelect('now');
    onClose();
  };

  const handleConfirm = () => {
    if (!selectedTime) return;
    const year = selectedDay.getFullYear();
    const month = String(selectedDay.getMonth() + 1).padStart(2, '0');
    const day = String(selectedDay.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    onSelect(`${dateStr} ${selectedTime}`);
    onClose();
  };

  const buttonLabel = useMemo(() => {
    if (!selectedTime) return 'Выберите время';

    const today = new Date();
    const isToday = selectedDay.toDateString() === today.toDateString();
    const isTomorrow = (() => {
      const tmr = new Date(today);
      tmr.setDate(today.getDate() + 1);
      return selectedDay.toDateString() === tmr.toDateString();
    })();

    const dayLabel = isToday
      ? 'Сегодня'
      : isTomorrow
      ? 'Завтра'
      : `${selectedDay.getDate()} ${MONTHS[selectedDay.getMonth()]}`;

    return `${dayLabel}, ${selectedTime}`;
  }, [selectedTime, selectedDay]);

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
        <button className="pos-close-inline" onClick={onClose} aria-label="Закрыть">✕</button>
        <Sheet.Content
          scrollRef={scrollRef}
          scrollClassName="pos-scroll"
        >
          <div className="pos-sheet">
            <h2 className="pos-title">Заказать ко времени</h2>

            <div className="pos-section-label">Дата</div>
            <div className="pos-days">
              {days.map((d, i) => {
                const isSelected = d.toDateString() === selectedDay.toDateString();
                return (
                  <button
                    key={i}
                    className={`pos-day ${isSelected ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedDay(d);
                      setSelectedTime(null);
                    }}
                  >
                    <span className="pos-day-num">{d.getDate()}</span>
                    <span className="pos-day-mon">{MONTHS[d.getMonth()]}</span>
                    <span className="pos-day-wd">
                      {i === 0 ? 'Сегодня' : i === 1 ? 'Завтра' : WEEKDAYS[d.getDay()]}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="pos-section-label">Время</div>

            <button
              className={`pos-time pos-time-asap ${isAsap ? 'active' : ''}`}
              onClick={handleAsap}
            >
              Как можно быстрее ~ 90 мин
            </button>

            <div className="pos-times">
              {availableSlots.length === 0 ? (
                <div className="pos-empty">
                  На сегодня время закончилось. Выберите другой день.
                </div>
              ) : (
                availableSlots.map((t) => (
                  <button
                    key={t}
                    className={`pos-time ${selectedTime === t ? 'active' : ''}`}
                    onClick={() => setSelectedTime(t)}
                  >
                    {t}
                  </button>
                ))
              )}
            </div>

            <button
              className="pos-btn"
              onClick={selectedTime ? handleConfirm : handleAsap}
              disabled={!selectedTime}
            >
              {buttonLabel}
            </button>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}