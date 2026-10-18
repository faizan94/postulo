"use client";

import { SlidersHorizontal } from "lucide-react";
import type { JobCard, WorkplaceType } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface Filters {
  work: WorkplaceType | "any";
  minMatch: 0 | 50 | 75;
  posted: 0 | 7 | 30;
  exactOnly: boolean;
}

export const NO_FILTERS: Filters = { work: "any", minMatch: 0, posted: 0, exactOnly: false };

export function applyFilters(cards: JobCard[], f: Filters): JobCard[] {
  const now = Date.now();
  return cards.filter((c) => {
    if (f.work !== "any" && c.workplace_type !== f.work) return false;
    if (f.minMatch && (c.match.value ?? 0) < f.minMatch) return false;
    if (f.posted) {
      if (!c.posted_at) return false;
      const days = (now - new Date(c.posted_at + "T00:00:00").getTime()) / 86_400_000;
      if (days > f.posted) return false;
    }
    if (f.exactOnly && c.related_role) return false;
    return true;
  });
}

function Seg<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { v: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex items-center gap-1.5" role="group" aria-label={label}>
      <span className="text-xs text-zinc-400">{label}</span>
      <div className="inline-flex rounded-lg bg-zinc-100 p-0.5">
        {options.map((o) => (
          <button
            key={String(o.v)}
            type="button"
            aria-pressed={value === o.v}
            onClick={() => onChange(o.v)}
            className={cn(
              "rounded-md px-2 py-0.5 text-xs",
              value === o.v ? "bg-white font-medium text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-800",
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Instant, client-side filters (D24). */
export function ResultFilters({
  value,
  onChange,
  shown,
  total,
}: {
  value: Filters;
  onChange: (f: Filters) => void;
  shown: number;
  total: number;
}) {
  const active =
    value.work !== "any" || value.minMatch !== 0 || value.posted !== 0 || value.exactOnly;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-zinc-200 bg-zinc-50/60 px-3 py-2">
      <SlidersHorizontal className="size-4 text-zinc-400" aria-hidden />
      <Seg
        label="Work"
        value={value.work}
        onChange={(work) => onChange({ ...value, work })}
        options={[
          { v: "any", label: "Any" },
          { v: "remote", label: "Remote" },
          { v: "hybrid", label: "Hybrid" },
          { v: "onsite", label: "On-site" },
        ]}
      />
      <Seg
        label="Match"
        value={value.minMatch}
        onChange={(minMatch) => onChange({ ...value, minMatch })}
        options={[
          { v: 0, label: "Any" },
          { v: 50, label: "50%+" },
          { v: 75, label: "75%+" },
        ]}
      />
      <Seg
        label="Posted"
        value={value.posted}
        onChange={(posted) => onChange({ ...value, posted })}
        options={[
          { v: 0, label: "Any" },
          { v: 7, label: "7 days" },
          { v: 30, label: "30 days" },
        ]}
      />
      <Seg
        label="Titles"
        value={value.exactOnly ? "exact" : "all"}
        onChange={(v) => onChange({ ...value, exactOnly: v === "exact" })}
        options={[
          { v: "all", label: "All" },
          { v: "exact", label: "Exact only" },
        ]}
      />
      <span className="ml-auto text-xs text-zinc-500">
        {shown} of {total}
        {active && (
          <button type="button" className="ml-2 text-indigo-700 hover:underline" onClick={() => onChange(NO_FILTERS)}>
            Clear
          </button>
        )}
      </span>
    </div>
  );
}
