// Small logo mark: rising bars inside a rounded square.
export default function Logo({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="DataSage logo">
      <rect width="32" height="32" rx="8" fill="#0b7a75" />
      <rect x="7" y="17" width="4.5" height="8" rx="1.2" fill="#fff" opacity="0.7" />
      <rect x="13.75" y="12" width="4.5" height="13" rx="1.2" fill="#fff" opacity="0.85" />
      <rect x="20.5" y="7" width="4.5" height="18" rx="1.2" fill="#fff" />
    </svg>
  );
}
