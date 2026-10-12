// frontend/src/components/CommentSheet.jsx
import { useState, useEffect } from 'react';
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import { cartComment } from '../api';
import './CommentSheet.css';

export default function CommentSheet({ open, userId, initialValue = '', onSaved, onClose }) {
  const [text, setText] = useState(initialValue);
  const [saving, setSaving] = useState(false);

  const { scrollRef } = useScrollPosition({ isEnabled: open });

  useEffect(() => {
    if (open) setText(initialValue || '');
  }, [open, initialValue]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await cartComment(userId, text);
      if (onSaved) await onSaved();
    } catch (e) {
      console.error('Ошибка сохранения комментария:', e);
    } finally {
      setSaving(false);
      onClose();
    }
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
          scrollRef={scrollRef}
          scrollClassName="cs-scroll"
        >
          <div className="cs-sheet">
            <h2 className="cs-title">Комментарий</h2>
            <textarea
              className="cs-textarea"
              placeholder="Комментарий"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              autoFocus
            />
            <button className="cs-save" onClick={handleSave} disabled={saving}>
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}