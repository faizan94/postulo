"use client";

import { useMutation } from "@tanstack/react-query";
import { AlertCircle, Info, RotateCw, SearchX, Workflow } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { Button } from "@/components/ui/button";
import { JobCardItem } from "@/features/results/JobCardItem";
import { LearnNext } from "@/features/results/LearnNext";
import { ProgressPanel } from "@/features/results/ProgressPanel";
import { SkillChart } from "@/features/results/SkillChart";
import { useSearchLive } from "@/features/search/useSearchLive";
import { api } from "@/lib/api";
import { formatDate, placesLabel } from "@/lib/format";
import type { JobCard } from "@/lib/types";
import { cn } from "@/lib/utils";

type Sort = "match" | "company";

function companySort(a: JobCard, b: JobCard) {
  return (b.company_score.value ?? -1) - (a.company_score.value ?? -1);
}

export default function SearchPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const { data, isLoading, error, stage, note } = useSearchLive(id);
  const [sort, setSort] = useState<Sort>("match");
  const rerun = useMutation({
    mutationFn: () => api.rerun(id),
    onSuccess: ({ search_id }) => router.push(`/search/${search_id}`),
    onError: (e) => toast.error(e.message),
  });

  const cards = useMemo(() => {
    const list = data?.results ?? [];
    return sort === "company" ? [...list].sort(companySort) : list;
  }, [data?.results, sort]);

  if (isLoading) return <FullPageSpinner />;
  if (error || !data)
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800">
        {error?.message ?? "Search not found."}
      </div>
    );

  const running = data.status === "queued" || data.status === "running";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-zinc-500">{formatDate(data.created_at)}</p>
          <h1 className="text-2xl font-semibold tracking-tight">{data.titles.join(" · ")}</h1>
          <p className="text-zinc-500">{placesLabel(data.places)}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => rerun.mutate()} disabled={running || rerun.isPending}>
            <RotateCw data-icon="inline-start" aria-hidden />
            Re-run
          </Button>
          <Button asChild>
            <Link href="/new-search">New search</Link>
          </Button>
        </div>
      </div>

      {running && <ProgressPanel stage={stage?.stage ?? data.stage} />}

      {note && (
        <p className="flex items-start gap-2 rounded-xl bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          {note}
        </p>
      )}

      {data.status === "failed" && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-800">
          <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">The search could not finish.</p>
            <p className="text-sm">{data.error}</p>
          </div>
        </div>
      )}

      {data.status === "done" && data.results.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <SkillChart items={data.skill_summary} />
          </div>
          <LearnNext items={data.learn_next} />
        </div>
      )}

      {cards.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold">
              {running ? "Matches so far" : `${cards.length} open jobs for you`}
            </h2>
            <div className="inline-flex rounded-lg bg-zinc-100 p-0.5 text-sm" role="group" aria-label="Sort by">
              {(["match", "company"] as Sort[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setSort(s)}
                  aria-pressed={sort === s}
                  className={cn(
                    "rounded-md px-3 py-1",
                    sort === s ? "bg-white font-medium text-zinc-900 shadow-sm" : "text-zinc-500",
                  )}
                >
                  {s === "match" ? "Best match" : "Company score"}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            {cards.map((c, i) => (
              <JobCardItem key={c.posting_id} card={c} rank={i + 1} searchId={id} />
            ))}
          </div>
        </section>
      )}

      {data.status === "done" && data.results.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-zinc-200 bg-white p-10 text-center">
          <SearchX className="size-8 text-zinc-300" aria-hidden />
          <p className="font-medium">No open matching jobs right now</p>
          <p className="max-w-md text-sm text-zinc-500">
            Try another job title, add a country or Remote, or run the search again later.
          </p>
          <Button asChild variant="outline">
            <Link href="/new-search">Change the search</Link>
          </Button>
        </div>
      )}

      {!running && (
        <div className="flex justify-center pt-4">
          <Link
            href={`/how/${id}`}
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700"
          >
            <Workflow className="size-3.5" aria-hidden />
            How this search worked
          </Link>
        </div>
      )}
    </div>
  );
}
