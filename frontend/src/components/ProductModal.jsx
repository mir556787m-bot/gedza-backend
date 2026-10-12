// frontend/src/components/ProductModal.jsx
import { Sheet, useScrollPosition } from 'react-modal-sheet';
import './ProductModal.css';

export default function ProductModal({
  product,
  qty = 0,
  open,
  onClose,
  onAdd,
  onChangeQty,
  onOpenCart,
}) {
  const { scrollRef } = useScrollPosition({ isEnabled: open });

  if (!product) return null;

  const inCart = qty > 0;
  const paragraphs = (product.description || '')
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <Sheet
      isOpen={open}
      onClose={onClose}
      detent="default"
      dragVelocityThreshold={1200}
      dragCloseThreshold={0.4}
      tweenConfig={{ ease: 'easeOut', duration: 0.4 }}
    >
      <Sheet.Container>
        <Sheet.Header />
        <Sheet.Content
          scrollRef={scrollRef}
          scrollClassName="pm-scroll"
        >
          <div className="pm-sheet">
            <div className="pm-image-wrap">
              <img src={product.image} alt={product.name} className="pm-image" />
              {product.badge && (
                <span className={`pm-badge badge-${product.badge.toLowerCase()}`}>
                  {product.badge}
                </span>
              )}
            </div>

            <div className="pm-body">
              <h2 className="pm-title">{product.name}</h2>
              {product.weight && <span className="pm-weight">{product.weight}</span>}
              {paragraphs.length > 0 && (
                <div className="pm-desc">
                  {paragraphs.map((p, i) => (
                    <p key={i}>{p}</p>
                  ))}
                </div>
              )}
            </div>

            <div className="pm-bottom">
              <div className="pm-actions">
                {!inCart ? (
                  <button className="pm-add-btn" onClick={onAdd}>
                    Добавить за {product.price} ₽ +
                  </button>
                ) : (
                  <div className="pm-qty-control">
                    <button className="pm-qty-btn" onClick={() => onChangeQty(-1)}>−</button>
                    <span className="pm-qty-info">{qty} × {product.price} ₽</span>
                    <button className="pm-qty-btn" onClick={() => onChangeQty(1)}>+</button>
                  </div>
                )}
                {inCart && (
                  <button
                    className="pm-cart-btn"
                    onClick={onOpenCart}
                    aria-label="Открыть корзину"
                  >
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <circle cx="9" cy="21" r="1" />
                      <circle cx="20" cy="21" r="1" />
                      <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>
        </Sheet.Content>
      </Sheet.Container>
      <Sheet.Backdrop />
    </Sheet>
  );
}