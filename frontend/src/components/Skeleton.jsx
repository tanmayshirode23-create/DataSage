// Grey placeholder shown while data loads, so the page doesn't jump around.
export function Skeleton({ height = 16, width = "100%", style }) {
  return <div className="skeleton" style={{ height, width, ...style }} aria-hidden="true" />;
}

export function ListSkeleton({ rows = 3 }) {
  return (
    <div className="panel" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-row">
          <div style={{ flex: 1 }}>
            <Skeleton height={16} width="45%" />
            <Skeleton height={12} width="30%" style={{ marginTop: 8 }} />
          </div>
          <Skeleton height={28} width={70} />
        </div>
      ))}
    </div>
  );
}

export function ReportSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading report">
      <Skeleton height={30} width="35%" />
      <Skeleton height={14} width="22%" style={{ marginTop: 10, marginBottom: 24 }} />
      <Skeleton height={230} style={{ marginBottom: 24 }} />
      <Skeleton height={260} />
    </div>
  );
}
