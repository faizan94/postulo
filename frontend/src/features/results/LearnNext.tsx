import { GraduationCap, TrendingUp } from "lucide-react";
import type { LearnNextItem } from "@/lib/types";

/**
 * Gap ROI: which skill missing from the CV would lift the most of your matches (§7.3).
 * "Missing" means not found in the CV, so the user may already have it and only needs to add it.
 */
export function LearnNext({ items }: { items: LearnNextItem[] }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <h2 className="flex items-center gap-2 font-semibold">
        <GraduationCap className="size-4 text-indigo-600" aria-hidden />
        Learn next or add to your CV
      </h2>
      <p className="mb-4 text-sm text-zinc-500">
        Skills these jobs want that aren&apos;t in your CV, top first. Already have one? Add it to
        your CV. If not, it&apos;s worth learning.
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-zinc-500">No clear gaps. You already cover these jobs well.</p>
      ) : (
        <ol className="space-y-3">
          {items.map((i, idx) => (
            <li key={i.skill} className="flex items-start gap-3">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700">
                {idx + 1}
              </span>
              <div className="min-w-0 text-sm">
                <p className="font-medium text-zinc-900">
                  {i.skill}
                  {i.slow && <span className="ml-2 text-xs font-normal text-zinc-400">takes longer</span>}
                </p>
                <p className="flex items-center gap-1 text-zinc-500">
                  <TrendingUp className="size-3.5 text-emerald-600" aria-hidden />+
                  {i.avg_gain_points} points on {i.jobs_improved} job{i.jobs_improved > 1 ? "s" : ""}
                  {i.unlocks > 0 && ` · fixes a must-have in ${i.unlocks}`}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
