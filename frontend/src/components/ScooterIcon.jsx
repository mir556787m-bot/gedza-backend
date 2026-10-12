// frontend/src/components/ScooterIcon.jsx
export default function ScooterIcon() {
  return (
    <svg viewBox="0 0 100 100" className="scooter-svg">
      {/* ЛИНИИ СКОРОСТИ */}
      <g className="speed-lines">
        <line
          x1="15" y1="40" x2="5" y2="40"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          className="line-top"
        />
        <line
          x1="12" y1="48" x2="2" y2="48"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          className="line-mid"
        />
        <line
          x1="18" y1="56" x2="8" y2="56"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          className="line-bot"
        />
      </g>

      {/* САМОКАТ */}
      <g className="scooter-body">
        <path
          d="M 68,45 L 68,70 L 40,70"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="68" cy="74" r="5" fill="currentColor" />
        <circle cx="40" cy="74" r="5" fill="currentColor" />
      </g>

      {/* ЧЕЛОВЕЧЕК */}
      <g className="rider">
        <circle cx="55" cy="30" r="5.5" fill="currentColor" />
        <path
          d="M 55,34 L 48,50 L 58,62 L 54,70"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M 53,38 L 62,45 L 68,45"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M 48,50 L 40,58 L 32,58"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="push-leg"
        />
      </g>
    </svg>
  );
}