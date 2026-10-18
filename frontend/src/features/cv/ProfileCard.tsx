"use client";

import { Briefcase, ChevronDown, GraduationCap, Languages, MapPin, Sparkles, UserRound } from "lucide-react";
import { useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Profile, SkillItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const GROUPS: { type: SkillItem["type"]; label: string; chip: string }[] = [
  { type: "tech", label: "Tools and technologies", chip: "bg-indigo-50 text-indigo-700 ring-indigo-200" },
  { type: "domain", label: "Domains", chip: "bg-sky-50 text-sky-700 ring-sky-200" },
  { type: "soft", label: "Ways of working", chip: "bg-zinc-100 text-zinc-700 ring-zinc-200" },
];

function period(start: string | null, end: string | null) {
  if (!start && !end) return "";
  const e = !end || end === "present" ? "now" : end;
  return `${start ?? "?"} – ${e}`;
}

function Chip({ s, chip }: { s: SkillItem; chip: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={cn("cursor-default rounded-full px-2 py-0.5 text-xs font-medium ring-1", chip)}>
          {s.name}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">From your CV: “{s.evidence.quote}”</TooltipContent>
    </Tooltip>
  );
}

/** "What we read from your CV" (D23). Every item except the AI summary has a CV quote. */
export function ProfileCard({ profile, collapsible = false }: { profile: Profile; collapsible?: boolean }) {
  const [open, setOpen] = useState(!collapsible);
  const facts = [
    profile.seniority && profile.seniority[0].toUpperCase() + profile.seniority.slice(1),
    profile.years_total != null && `${profile.years_total} years experience`,
  ].filter(Boolean);

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <button
        type="button"
        className="flex w-full items-start justify-between gap-3 text-left"
        onClick={() => collapsible && setOpen(!open)}
        aria-expanded={open}
        disabled={!collapsible}
      >
        <div className="flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
            <UserRound className="size-4" aria-hidden />
          </span>
          <div>
            <p className="text-xs font-medium tracking-wide text-zinc-400 uppercase">What we read from your CV</p>
            <p className="font-semibold text-zinc-900">{profile.headline ?? "Your profile"}</p>
            <p className="flex flex-wrap items-center gap-x-3 text-sm text-zinc-500">
              {facts.join(" · ")}
              {profile.place && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="size-3.5" aria-hidden />
                  {profile.place.name}
                </span>
              )}
              <span>{profile.skills.length} skills found</span>
            </p>
          </div>
        </div>
        {collapsible && (
          <ChevronDown className={cn("mt-2 size-4 shrink-0 text-zinc-400 transition", open && "rotate-180")} aria-hidden />
        )}
      </button>

      {open && (
        <div className="mt-4 space-y-5">
          {profile.summary && (
            <div className="rounded-xl bg-zinc-50 p-3 text-sm text-zinc-700">
              <p className="mb-1 flex items-center gap-1 text-xs font-medium text-zinc-400">
                <Sparkles className="size-3" aria-hidden />
                AI summary of your CV
              </p>
              {profile.summary}
            </div>
          )}

          {GROUPS.map((g) => {
            const items = profile.skills.filter((s) => s.type === g.type);
            if (!items.length) return null;
            return (
              <div key={g.type} className="space-y-2">
                <h3 className="text-sm font-medium text-zinc-700">
                  {g.label} <span className="text-zinc-400">({items.length})</span>
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {items.map((s) => (
                    <Chip key={s.name} s={s} chip={g.chip} />
                  ))}
                </div>
              </div>
            );
          })}

          {profile.roles.length > 0 && (
            <div className="space-y-2">
              <h3 className="flex items-center gap-1.5 text-sm font-medium text-zinc-700">
                <Briefcase className="size-4 text-zinc-400" aria-hidden />
                Experience
              </h3>
              <ol className="space-y-1.5 text-sm">
                {profile.roles.map((r, i) => (
                  <li key={i} className="flex flex-wrap justify-between gap-x-3">
                    <span className="text-zinc-800">
                      {r.title}
                      {r.company && <span className="text-zinc-500"> · {r.company}</span>}
                    </span>
                    <span className="text-xs text-zinc-400 tabular-nums">{period(r.start, r.end)}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            {profile.languages.length > 0 && (
              <div className="space-y-1.5">
                <h3 className="flex items-center gap-1.5 text-sm font-medium text-zinc-700">
                  <Languages className="size-4 text-zinc-400" aria-hidden />
                  Languages
                </h3>
                <p className="text-sm text-zinc-600">
                  {profile.languages.map((l) => (l.level ? `${l.name} (${l.level})` : l.name)).join(", ")}
                </p>
              </div>
            )}
            {profile.education.length > 0 && (
              <div className="space-y-1.5">
                <h3 className="flex items-center gap-1.5 text-sm font-medium text-zinc-700">
                  <GraduationCap className="size-4 text-zinc-400" aria-hidden />
                  Education
                </h3>
                <ul className="text-sm text-zinc-600">
                  {profile.education.map((e, i) => (
                    <li key={i}>{[e.degree, e.school].filter(Boolean).join(", ")}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {profile.target_titles.length > 0 && (
            <p className="text-sm text-zinc-500">
              Suggested roles: <span className="text-zinc-800">{profile.target_titles.join(", ")}</span>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
