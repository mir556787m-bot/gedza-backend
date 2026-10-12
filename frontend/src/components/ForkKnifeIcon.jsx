// frontend/src/components/icons/ForkKnifeIcon.jsx
export default function ForkKnifeIcon({ size = 22, color = 'currentColor' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Вилка: основание и ручка */}
      <path
        d="M22 10V24C22 28 25 31 28 31V54C28 55.1 28.9 56 30 56C31.1 56 32 55.1 32 54V31C35 31 38 28 38 24V10"
        stroke={color}
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Внутренние зубцы вилки */}
      <path
        d="M27 10V20M33 10V20"
        stroke={color}
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />
      {/* Нож */}
      <path
        d="M46 10C41 10 40 15 40 24V34H44V54C44 55.1 44.9 56 46 56C47.1 56 48 55.1 48 54V10H46Z"
        fill={color}
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}