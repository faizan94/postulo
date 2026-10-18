import type { Skill, SkillStatus } from "@/lib/types";

const STYLES: Record<SkillStatus, string> = {
  gold: "bg-amber-100 text-amber-900 ring-amber-300",
  orange: "bg-orange-100 text-orange-900 ring-orange-300",
  red: "bg-red-100 text-red-900 ring-red-300",
};

export const STATUS_LABEL: Record<SkillStatus, string> = {
  gold: "You have it",
  orange: "Gap worth covering",
  red: "Important gap",
};

export function SkillDot({ status }: { status: SkillStatus }) {
  const color = {
    gold: "bg-amber-400",
    orange: "bg-orange-500",
    red: "bg-red-600",
  }[status];
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

export function SkillChip({ skill }: { skill: Skill }) {
  const title = [STATUS_LABEL[skill.status], skill.note]
    .filter(Boolean)
    .join(": ");
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STYLES[skill.status]}`}
    >
      <SkillDot status={skill.status} />
      {skill.name}
    </span>
  );
}
