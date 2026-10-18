import { Building2 } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BAND, STATUS } from "@/lib/status";
import type { CompanyScore, SkillMatch, SkillStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function CompanyScoreBadge({ score }: { score: CompanyScore }) {
  const band = BAND[score.band];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1",
        band.chip,
        score.band === "pending" && "animate-pulse",
      )}
    >
      <Building2 className="size-3" aria-hidden />
      Company: {band.label}
      {score.value !== null && <span className="tabular-nums opacity-80">{score.value}</span>}
    </span>
  );
}

export function SkillChip({ match }: { match: SkillMatch }) {
  const s = STATUS[match.status];
  const Icon = s.icon;
  const r = match.requirement;
  const label = r.type === "years" ? `${r.min_years ?? ""}+ yrs` : r.level ? `${r.name} ${r.level}` : r.name;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex cursor-default items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1",
            s.chip,
          )}
        >
          <Icon className="size-3" aria-hidden />
          {label}
          <span className="sr-only">: {s.label}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p className="font-medium">
          {s.label} · {r.importance === "must" ? "required" : "nice to have"}
        </p>
        <p className="mt-1 opacity-80">“{r.evidence.quote}”</p>
        {match.cv_evidence && <p className="mt-1 opacity-80">Your CV: “{match.cv_evidence.quote}”</p>}
      </TooltipContent>
    </Tooltip>
  );
}

export function StatusLegend({ statuses = ["have", "related", "missing_nice", "missing_must"] }: {
  statuses?: SkillStatus[];
}) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
      {statuses.map((k) => {
        const s = STATUS[k];
        const Icon = s.icon;
        return (
          <li key={k} className="inline-flex items-center gap-1.5">
            <span className={cn("flex size-4 items-center justify-center rounded-full text-white", s.dot)}>
              <Icon className="size-2.5" aria-hidden />
            </span>
            {s.label}
          </li>
        );
      })}
    </ul>
  );
}
