import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight text-zinc-900">
      <span className="flex size-7 items-center justify-center rounded-lg bg-indigo-600 text-sm text-white">
        P
      </span>
      Postulo
    </Link>
  );
}
