"use client";

import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { STATUS } from "@/lib/status";
import type { SkillStatus, SkillSummaryItem } from "@/lib/types";
import { StatusLegend } from "./Badges";

const config = {
  must: { label: "Required" },
  nice: { label: "Nice to have" },
} satisfies ChartConfig;

function statusOf(item: SkillSummaryItem): SkillStatus {
  if (item.user_status === "have") return "have";
  if (item.user_status === "related") return "related";
  return item.must_count > 0 ? "missing_must" : "missing_nice";
}

/** Skills asked for across your matches: length = demand, color = your status (§8.3). */
export function SkillChart({ items }: { items: SkillSummaryItem[] }) {
  const data = items.slice(0, 10).map((i) => ({
    skill: i.skill,
    must: i.must_count,
    nice: i.demand - i.must_count,
    status: statusOf(i),
    label: `${i.demand} of ${i.of} jobs`,
  }));
  const total = items[0]?.of ?? 0;
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <h2 className="font-semibold">Skills these jobs ask for</h2>
        <span className="text-xs text-zinc-400">in these {total} jobs</span>
      </div>
      <p className="mb-4 text-sm text-zinc-500">Darker part = required, lighter = nice to have.</p>
      <ChartContainer config={config} className="aspect-auto w-full" style={{ height: 32 * data.length + 24 }}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16, top: 0, bottom: 0 }} barCategoryGap={6}>
          <CartesianGrid horizontal={false} stroke="oklch(0.967 0.001 286.375)" />
          <XAxis type="number" allowDecimals={false} domain={[0, total || "auto"]} tickLine={false} axisLine={false} fontSize={11} />
          <YAxis type="category" dataKey="skill" width={120} tickLine={false} axisLine={false} fontSize={12} />
          <ChartTooltip
            cursor={{ fill: "oklch(0.985 0 0)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as (typeof data)[number];
              return (
                <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs shadow-md">
                  <p className="font-medium">{d.skill}</p>
                  <p className="text-zinc-500">
                    {d.label} · {d.must} required
                  </p>
                  <p className="mt-1">{STATUS[d.status].label}</p>
                </div>
              );
            }}
          />
          <Bar dataKey="must" stackId="a" radius={[4, 0, 0, 4]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.skill} fill={STATUS[d.status].fill} />
            ))}
          </Bar>
          <Bar dataKey="nice" stackId="a" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.skill} fill={STATUS[d.status].fill} fillOpacity={0.4} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>
      <div className="mt-3">
        <StatusLegend />
      </div>
    </div>
  );
}
