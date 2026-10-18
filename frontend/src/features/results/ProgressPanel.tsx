import { Check, Loader2 } from "lucide-react";
import type { Stage } from "@/lib/types";
import { cn } from "@/lib/utils";

const ORDER: { stage: Stage; label: string }[] = [
  { stage: "planning", label: "Planning your search" },
  { stage: "searching", label: "Searching job boards" },
  { stage: "checking", label: "Checking openings are still open" },
  { stage: "reading", label: "Reading the full job posts" },
  { stage: "matching", label: "Matching jobs to your skills" },
  { stage: "company", label: "Looking at the companies" },
  { stage: "ranking", label: "Ranking your best matches" },
];

/** Plain-words progress (D14). No counts of dropped jobs. */
export function ProgressPanel({ stage }: { stage: Stage | null }) {
  const current = stage ? ORDER.findIndex((o) => o.stage === stage) : 0;
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm" role="status">
      <p className="mb-4 font-medium">Finding your matches…</p>
      <ol className="grid gap-2 sm:grid-cols-2">
        {ORDER.map((o, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li key={o.stage} className="flex items-center gap-2.5 text-sm">
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full",
                  done && "bg-emerald-500 text-white",
                  active && "bg-indigo-50 text-indigo-600",
                  !done && !active && "bg-zinc-100",
                )}
              >
                {done ? (
                  <Check className="size-3" aria-hidden />
                ) : active ? (
                  <Loader2 className="size-3 animate-spin" aria-hidden />
                ) : null}
              </span>
              <span className={cn(done || active ? "text-zinc-900" : "text-zinc-400")}>
                {o.label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
