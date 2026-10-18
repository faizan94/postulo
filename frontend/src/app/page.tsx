"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { homePath, useAuth } from "@/features/auth/AuthProvider";

export default function Home() {
  const { ready, me } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!ready) return;
    router.replace(me ? homePath(me) : "/login");
  }, [ready, me, router]);
  return <FullPageSpinner />;
}
