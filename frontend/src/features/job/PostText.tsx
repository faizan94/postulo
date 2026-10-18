import { STATUS } from "@/lib/status";
import type { SkillMatch } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Mark {
  start: number;
  end: number;
  match: SkillMatch;
}

function findMarks(text: string, skills: SkillMatch[]): Mark[] {
  const lower = text.toLowerCase();
  const marks: Mark[] = [];
  for (const m of skills) {
    const q = m.requirement.evidence.quote.trim().toLowerCase();
    if (q.length < 2) continue;
    const start = lower.indexOf(q);
    if (start === -1) continue;
    marks.push({ start, end: start + q.length, match: m });
  }
  marks.sort((a, b) => a.start - b.start);
  const clean: Mark[] = [];
  for (const mk of marks) if (!clean.length || mk.start >= clean[clean.length - 1].end) clean.push(mk);
  return clean;
}

/** The post exactly as fetched (D15), with the quoted requirements highlighted by status. */
export function PostText({ text, skills }: { text: string; skills: SkillMatch[] }) {
  const marks = findMarks(text, skills);
  const parts: React.ReactNode[] = [];
  let pos = 0;
  marks.forEach((mk, i) => {
    if (mk.start > pos) parts.push(text.slice(pos, mk.start));
    parts.push(
      <mark
        key={i}
        title={`${mk.match.requirement.name}: ${STATUS[mk.match.status].label}`}
        className={cn("rounded px-0.5 ring-1", STATUS[mk.match.status].chip)}
      >
        {text.slice(mk.start, mk.end)}
      </mark>,
    );
    pos = mk.end;
  });
  if (pos < text.length) parts.push(text.slice(pos));
  return (
    <div className="text-sm leading-relaxed whitespace-pre-line text-zinc-700">{parts}</div>
  );
}
