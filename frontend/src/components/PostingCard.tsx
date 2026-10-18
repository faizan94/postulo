import type { Posting, SkillStatus } from "@/lib/types";
import { SkillChip } from "./SkillChip";
import { StarScore } from "./StarScore";
import { VerifiedBadges } from "./VerifiedBadges";

const ORDER: Record<SkillStatus, number> = { gold: 0, orange: 1, red: 2 };

export function PostingCard({ posting, rank }: { posting: Posting; rank: number }) {
  const skills = [...posting.skills].sort(
    (a, b) => ORDER[a.status] - ORDER[b.status],
  );
  const gold = skills.filter((s) => s.status === "gold").length;
  const meta = [posting.location, posting.posted && `posted ${posting.posted}`, posting.source]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">
            #{rank} · {posting.company}
          </p>
          <h3 className="mt-0.5 text-lg font-semibold text-zinc-900">
            <a
              href={posting.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
            >
              {posting.title}
            </a>
          </h3>
          {meta && <p className="mt-0.5 text-sm text-zinc-500">{meta}</p>}
        </div>
        <StarScore score={posting.score} />
      </div>

      <div className="mt-3">
        <VerifiedBadges verified={posting.verified} />
      </div>

      {skills.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs text-zinc-500">
            {gold}/{skills.length} skills matched
          </p>
          <div className="flex flex-wrap gap-1.5">
            {skills.map((s) => (
              <SkillChip key={s.name} skill={s} />
            ))}
          </div>
        </div>
      )}

      {posting.why && (
        <p className="mt-4 rounded-lg bg-zinc-50 p-3 text-sm leading-relaxed text-zinc-700">
          <span className="font-medium text-zinc-900">Why: </span>
          {posting.why}
        </p>
      )}
    </article>
  );
}
