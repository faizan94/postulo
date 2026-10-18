import type { AgentStep, RejectedPosting } from "@/lib/types";

const AGENT_STYLE: Record<AgentStep["agent"], string> = {
  orchestrator: "bg-zinc-900 text-white",
  search: "bg-sky-100 text-sky-800",
  verify: "bg-emerald-100 text-emerald-800",
  score: "bg-violet-100 text-violet-800",
};

export function AgentTrace({
  trace,
  rejected,
}: {
  trace: AgentStep[];
  rejected: RejectedPosting[];
}) {
  return (
    <aside className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-zinc-900">Agent trace</h2>
        <ol className="space-y-2">
          {trace.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span
                className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${AGENT_STYLE[step.agent]}`}
              >
                {step.agent}
              </span>
              <span className="text-zinc-700">
                {step.message}
                {step.duration_ms != null && (
                  <span className="ml-1 text-zinc-400">
                    ({(step.duration_ms / 1000).toFixed(1)}s)
                  </span>
                )}
              </span>
            </li>
          ))}
        </ol>
      </div>

      {rejected.length > 0 && (
        <div className="rounded-2xl border border-red-200 bg-red-50/50 p-4">
          <h2 className="mb-3 text-sm font-semibold text-red-900">
            {rejected.length} ghost / dead postings removed
          </h2>
          <ul className="space-y-2">
            {rejected.map((r) => (
              <li key={r.url} className="text-sm">
                <p className="font-medium text-zinc-800 line-through">
                  {r.title}
                  {r.company && ` · ${r.company}`}
                </p>
                <p className="text-xs text-red-700">{r.reason}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
