import { CalendarDays, ChevronRight, MapPin } from "lucide-react";
import Link from "next/link";
import { daysAgo, placeLabel, WORKPLACE } from "@/lib/format";
import type { JobCard } from "@/lib/types";
import { CompanyScoreBadge, SkillChip } from "./Badges";
import { MatchScoreRing } from "./MatchScoreRing";

export function JobCardItem({ card, rank, searchId }: { card: JobCard; rank: number; searchId: number }) {
  const posted = daysAgo(card.posted_at);
  return (
    <Link
      href={`/search/${searchId}/job/${card.posting_id}`}
      className="group block rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md focus-visible:ring-3 focus-visible:ring-indigo-200 focus-visible:outline-none"
    >
      <div className="flex items-start gap-4">
        <MatchScoreRing value={card.match.value} />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium text-zinc-400">#{rank}</p>
              <h3 className="truncate font-semibold text-zinc-900 group-hover:text-indigo-700">
                {card.title}
              </h3>
              <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-500">
                <span className="font-medium text-zinc-700">{card.company}</span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="size-3.5" aria-hidden />
                  {placeLabel(card.place)}
                  {card.workplace_type && ` · ${WORKPLACE[card.workplace_type]}`}
                </span>
                {posted && (
                  <span className="inline-flex items-center gap-1">
                    <CalendarDays className="size-3.5" aria-hidden />
                    {posted}
                  </span>
                )}
              </p>
            </div>
            <ChevronRight className="mt-5 size-5 shrink-0 text-zinc-300 group-hover:text-indigo-500" aria-hidden />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <CompanyScoreBadge score={card.company_score} />
            <span className="text-xs text-zinc-500">
              Must-haves {card.match.must_met} · Nice-to-haves {card.match.nice_met}
            </span>
          </div>
          {card.top_skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {card.top_skills.map((m) => (
                <SkillChip key={m.requirement.name} match={m} />
              ))}
            </div>
          )}
          {card.match.gates_applied.length > 0 && (
            <p className="text-xs text-rose-600">Capped: {card.match.gates_applied.join(", ")}</p>
          )}
        </div>
      </div>
    </Link>
  );
}
