// One map for status -> color, icon, label (PHASE1_PLAN.md §8.3). Used everywhere.
import { AlertTriangle, Check, Shuffle, X, type LucideIcon } from "lucide-react";
import type { CompanyBand, SkillStatus } from "@/lib/types";

export const STATUS: Record<
  SkillStatus,
  { label: string; icon: LucideIcon; chip: string; dot: string; fill: string }
> = {
  have: {
    label: "You have it",
    icon: Check,
    chip: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    dot: "bg-emerald-500",
    fill: "oklch(0.696 0.17 162.48)",
  },
  related: {
    label: "Close match",
    icon: Shuffle,
    chip: "bg-sky-50 text-sky-700 ring-sky-200",
    dot: "bg-sky-500",
    fill: "oklch(0.685 0.169 237.323)",
  },
  missing_nice: {
    label: "Nice-to-have gap",
    icon: AlertTriangle,
    chip: "bg-amber-50 text-amber-700 ring-amber-200",
    dot: "bg-amber-500",
    fill: "oklch(0.769 0.188 70.08)",
  },
  missing_must: {
    label: "Must-have gap",
    icon: X,
    chip: "bg-rose-50 text-rose-700 ring-rose-200",
    dot: "bg-rose-500",
    fill: "oklch(0.645 0.246 16.439)",
  },
};

export const BAND: Record<CompanyBand, { label: string; chip: string }> = {
  strong: { label: "Strong", chip: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  okay: { label: "Okay", chip: "bg-amber-50 text-amber-700 ring-amber-200" },
  weak: { label: "Weak", chip: "bg-rose-50 text-rose-700 ring-rose-200" },
  not_enough_data: { label: "Not enough data", chip: "bg-zinc-50 text-zinc-600 ring-zinc-200" },
  pending: { label: "Checking…", chip: "bg-zinc-50 text-zinc-400 ring-zinc-200" },
};

export function matchTone(value: number | null): string {
  if (value === null) return "text-zinc-400";
  if (value >= 75) return "text-emerald-600";
  if (value >= 50) return "text-indigo-600";
  return "text-amber-600";
}
