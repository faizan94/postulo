"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Bot, Coins, Filter, Workflow } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { api } from "@/lib/api";

/** Trace view (D14): the agent trace, quiet drops and usage. Not linked in the main flow. */
export default function HowPage() {
  const id = Number(useParams<{ id: string }>().id);
  const { data, isLoading, error } = useQuery({ queryKey: ["how", id], queryFn: () => api.how(id) });
  if (isLoading) return <FullPageSpinner />;
  if (error || !data) return <p className="text-rose-700">{error?.message ?? "Not found."}</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link href={`/search/${id}`} className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-900">
        <ArrowLeft className="size-4" aria-hidden />
        Back to matches
      </Link>
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Workflow className="size-6 text-indigo-600" aria-hidden />
          How this search worked
        </h1>
        <p className="text-zinc-500">
          The agent&apos;s steps, the postings it removed quietly, and what it cost.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { icon: Coins, label: "Tavily credits", value: data.usage.tavily_credits },
          { icon: Bot, label: "Nemotron calls", value: data.usage.llm_calls },
          { icon: Filter, label: "Removed quietly", value: data.dropped.length },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <p className="flex items-center gap-1.5 text-sm text-zinc-500">
              <Icon className="size-4" aria-hidden />
              {label}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-semibold">Agent trace</h2>
        <ol className="relative space-y-4 border-l border-zinc-200 pl-5">
          {data.trace.map((t, i) => (
            <li key={i} className="relative">
              <span className="absolute top-1.5 -left-[25px] size-2.5 rounded-full bg-indigo-500 ring-4 ring-white" />
              <p className="text-xs font-medium tracking-wide text-indigo-600 uppercase">{t.stage}</p>
              <p className="text-sm text-zinc-800">{t.message}</p>
              {Object.keys(t.data).length > 0 && (
                <pre className="mt-1 overflow-x-auto rounded-lg bg-zinc-50 p-2 text-[11px] text-zinc-500">
                  {JSON.stringify(t.data, null, 1)}
                </pre>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="mb-1 font-semibold">Postings removed quietly</h2>
        <p className="mb-4 text-sm text-zinc-500">Job seekers never see these. Shown here for transparency.</p>
        {data.dropped.length === 0 ? (
          <p className="text-sm text-zinc-500">None.</p>
        ) : (
          <ul className="divide-y divide-zinc-100 text-sm">
            {data.dropped.map((d) => (
              <li key={d.url} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
                <a href={d.url} target="_blank" rel="noopener noreferrer" className="truncate text-zinc-800 hover:underline">
                  {d.title}
                  {d.company && <span className="text-zinc-400"> · {d.company}</span>}
                </a>
                <span className="text-xs text-rose-600">{d.reason}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
