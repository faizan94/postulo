import { PostuloFlow } from "@/components/PostuloFlow";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900">
          Postulo
        </h1>
        <p className="mt-1 text-zinc-600">
          LinkedIn shows you jobs. Postulo tells you which ones are real, why
          you fit, and what&apos;s missing.
        </p>
      </header>
      <PostuloFlow />
      <footer className="mt-12 text-xs text-zinc-400">
        NVIDIA Nemotron on Nebius Token Factory · search by Tavily
      </footer>
    </main>
  );
}
