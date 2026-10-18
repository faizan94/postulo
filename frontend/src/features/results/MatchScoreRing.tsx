"use client";

import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts";
import { cn } from "@/lib/utils";
import { matchTone } from "@/lib/status";

const COLOR = (v: number | null) =>
  v === null
    ? "oklch(0.871 0.006 286.286)"
    : v >= 75
      ? "oklch(0.696 0.17 162.48)"
      : v >= 50
        ? "oklch(0.511 0.262 276.966)"
        : "oklch(0.769 0.188 70.08)";

/** Small radial ring with the match % in the middle (§8.3). */
export function MatchScoreRing({ value, size = 64 }: { value: number | null; size?: number }) {
  const data = [{ v: value ?? 0 }];
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <RadialBarChart
        width={size}
        height={size}
        data={data}
        innerRadius="78%"
        outerRadius="100%"
        startAngle={90}
        endAngle={-270}
        barSize={6}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} axisLine={false} />
        <RadialBar
          dataKey="v"
          cornerRadius={6}
          background={{ fill: "oklch(0.967 0.001 286.375)" }}
          fill={COLOR(value)}
          isAnimationActive={false}
        />
      </RadialBarChart>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className={cn("text-base font-semibold tabular-nums", matchTone(value))}>
          {value === null ? "–" : `${value}%`}
        </span>
        <span className="mt-0.5 text-[10px] text-zinc-400">match</span>
      </div>
    </div>
  );
}
