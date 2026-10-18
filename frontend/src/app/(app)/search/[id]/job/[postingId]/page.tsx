"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, CalendarDays, ExternalLink, MapPin } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { Button } from "@/components/ui/button";
import { PostText } from "@/features/job/PostText";
import { CompanyScoreBadge, SkillChip, StatusLegend } from "@/features/results/Badges";
import { MatchScoreRing } from "@/features/results/MatchScoreRing";
import { api } from "@/lib/api";
import { daysAgo, placeLabel, WORKPLACE } from "@/lib/format";
import type { SkillMatch, SkillStatus } from "@/lib/types";

const GROUPS: { title: string; statuses: SkillStatus[] }[] = [
  { title: "Missing must-haves", statuses: ["missing_must"] },
  { title: "You already have", statuses: ["have", "related"] },
  { title: "Nice to have, missing", statuses: ["missing_nice"] },
];

function Group({ title, items }: { title: string; items: SkillMatch[] }) {
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-zinc-700">
        {title} <span className="text-zinc-400">({items.length})</span>
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {items.map((m) => (
          <SkillChip key={m.requirement.name} match={m} />
        ))}
      </div>
    </div>
  );
}

export default function JobPage() {
  const params = useParams<{ id: string; postingId: string }>();
  const searchId = Number(params.id);
  const postingId = Number(params.postingId);
  const { data, isLoading, error } = useQuery({
    queryKey: ["posting", postingId, searchId],
    queryFn: () => api.posting(postingId, searchId),
  });

  if (isLoading) return <FullPageSpinner />;
  if (error || !data)
    return <p className="rounded-xl bg-rose-50 p-4 text-rose-700">{error?.message ?? "Not found."}</p>;

  const posted = daysAgo(data.posted_at);
  return (
    <div className="space-y-6">
      <Link
        href={`/search/${searchId}`}
        className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-900"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Back to matches
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{data.title}</h1>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-zinc-500">
            <span className="inline-flex items-center gap-1 font-medium text-zinc-700">
              <Building2 className="size-4" aria-hidden />
              {data.company}
            </span>
            <span className="inline-flex items-center gap-1">
              <MapPin className="size-4" aria-hidden />
              {placeLabel(data.place)}
              {data.workplace_type && ` · ${WORKPLACE[data.workplace_type]}`}
            </span>
            {posted && (
              <span className="inline-flex items-center gap-1">
                <CalendarDays className="size-4" aria-hidden />
                Posted {posted}
              </span>
            )}
          </p>
        </div>
        <Button asChild size="lg" className="h-10">
          <a href={data.apply_url} target="_blank" rel="noopener noreferrer">
            Apply on company site
            <ExternalLink data-icon="inline-end" aria-hidden />
          </a>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <aside className="space-y-6 lg:order-2">
          <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold">Your match</h2>
            <div className="flex items-center gap-4">
              <MatchScoreRing value={data.match.value} size={84} />
              <dl className="space-y-1 text-sm">
                <div className="flex gap-2">
                  <dt className="text-zinc-500">Must-haves met</dt>
                  <dd className="font-medium tabular-nums">{data.match.must_met}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="text-zinc-500">Nice-to-haves met</dt>
                  <dd className="font-medium tabular-nums">{data.match.nice_met}</dd>
                </div>
              </dl>
            </div>
            {data.match.gates_applied.length > 0 && (
              <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
                Score capped: {data.match.gates_applied.join(", ")}
              </p>
            )}
            {data.match.thin && (
              <p className="rounded-lg bg-zinc-50 px-3 py-2 text-xs text-zinc-500">
                This post lists few requirements, so the score is less certain.
              </p>
            )}
            {GROUPS.map((g) => (
              <Group
                key={g.title}
                title={g.title}
                items={data.skills.filter(
                  (m) => g.statuses.includes(m.status) && m.requirement.type !== "degree",
                )}
              />
            ))}
            <StatusLegend />
          </div>

          <div className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-semibold">Company</h2>
              <CompanyScoreBadge score={data.company_score} />
            </div>
            <p className="text-xs text-zinc-500">Based only on public hiring signals.</p>
            <ul className="space-y-1.5 text-sm">
              {data.company_score.sources.map((s) => (
                <li key={s.url}>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-indigo-700 hover:underline"
                  >
                    {s.title}
                    <ExternalLink className="size-3" aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <article className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm lg:order-1 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="font-semibold">Full job post</h2>
            <a
              href={data.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-700"
            >
              Original post <ExternalLink className="size-3" aria-hidden />
            </a>
          </div>
          <PostText text={data.full_text} skills={data.skills} />
        </article>
      </div>
    </div>
  );
}
