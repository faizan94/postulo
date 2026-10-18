"use client";

import { History, LogOut, Plus, Settings, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/AuthProvider";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/new-search", label: "New search", icon: Plus },
  { href: "/history", label: "History", icon: History },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { ready, me, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ready && !me) router.replace("/login");
  }, [ready, me, router]);

  if (!ready || !me) return <FullPageSpinner />;

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
          <Logo />
          <nav className="flex items-center gap-1" aria-label="Main">
            {NAV.map(({ href, label, icon: Icon }) => (
              <Button
                key={href}
                asChild
                variant="ghost"
                size="sm"
                className={cn(pathname.startsWith(href) && "bg-zinc-100 text-zinc-900")}
              >
                <Link href={href}>
                  <Icon data-icon="inline-start" aria-hidden />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              </Button>
            ))}
            <span className="mx-2 hidden h-5 w-px bg-zinc-200 sm:block" />
            <span className="hidden max-w-32 truncate text-sm text-zinc-500 md:inline">
              {me.user.name}
            </span>
            <Button variant="ghost" size="icon-sm" onClick={logout} aria-label="Log out">
              <LogOut aria-hidden />
            </Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
