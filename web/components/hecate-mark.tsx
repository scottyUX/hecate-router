/** The Hecate tripod mark from the slide deck: three ink arms around an accent dot. */
export function HecateMark({ className = "size-5" }: { className?: string }) {
  return (
    <svg
      viewBox="-180 -180 360 360"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {[0, 120, 240].map((angle) => (
        <rect
          key={angle}
          x={-23}
          y={-160}
          width={46}
          height={110}
          fill="currentColor"
          transform={`rotate(${angle})`}
        />
      ))}
      <circle r={30} fill="var(--hc-accent, #e95526)" />
    </svg>
  );
}
