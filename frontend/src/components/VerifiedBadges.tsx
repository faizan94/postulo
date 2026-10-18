import type { VerifiedFlags } from "@/lib/types";

const LABELS: Record<keyof VerifiedFlags, string> = {
  company_exists: "Company verified",
  posting_live: "Posting live",
  recent: "Recent",
};

export function VerifiedBadges({ verified }: { verified: VerifiedFlags }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {(Object.keys(LABELS) as (keyof VerifiedFlags)[]).map((key) => {
        const ok = verified[key];
        return (
          <span
            key={key}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium ${
              ok
                ? "bg-emerald-50 text-emerald-700"
                : "bg-zinc-100 text-zinc-500 line-through"
            }`}
          >
            {ok ? "✓" : "✕"} {LABELS[key]}
          </span>
        );
      })}
    </div>
  );
}
