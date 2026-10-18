import { Suspense } from "react";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { AppShell } from "@/features/shell/AppShell";

// Cache Components: URL hooks (usePathname, useParams) must render inside <Suspense>.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<FullPageSpinner />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
