export function StarScore({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(5, score)) * 20;
  return (
    <span
      className="inline-flex items-center gap-1.5"
      aria-label={`${score} out of 5 stars`}
    >
      <span className="relative inline-block text-lg leading-none tracking-tight">
        <span className="text-zinc-300">★★★★★</span>
        <span
          className="absolute inset-0 overflow-hidden whitespace-nowrap text-amber-500"
          style={{ width: `${pct}%` }}
        >
          ★★★★★
        </span>
      </span>
      <span className="text-sm font-semibold text-zinc-700">
        {score.toFixed(1)}
      </span>
    </span>
  );
}
