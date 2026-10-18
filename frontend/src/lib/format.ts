import type { Place, WorkplaceType } from "@/lib/types";

export function daysAgo(iso: string | null): string | null {
  if (!iso) return null;
  const then = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  const days = Math.max(0, Math.round((Date.now() - then.getTime()) / 86_400_000));
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  return `${months} month${months > 1 ? "s" : ""} ago`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function placeLabel(p: Place | null): string {
  if (!p) return "Location not stated";
  return p.name;
}

export const WORKPLACE: Record<WorkplaceType, string> = {
  onsite: "On-site",
  hybrid: "Hybrid",
  remote: "Remote",
};

export function placesLabel(places: Place[]): string {
  return places.map((p) => p.name).join(", ");
}
