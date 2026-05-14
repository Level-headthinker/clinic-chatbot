export function SkeletonBlock({ className = "" }) {
  return <div className={`skeleton ${className}`} />;
}

export function DashboardSkeleton() {
  return (
    <>
      <div className="metric-grid">
        {[1, 2, 3, 4].map((item) => (
          <SkeletonBlock key={item} className="metric-card skeleton-card" />
        ))}
      </div>
      <SkeletonBlock className="panel skeleton-table" />
    </>
  );
}
