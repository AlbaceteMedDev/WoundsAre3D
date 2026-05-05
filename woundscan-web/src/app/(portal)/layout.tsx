import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";

/**
 * Authentication gate + space for the portal AppShell. Each page renders
 * its own AppShell so the title/subtitle can be page-specific while
 * still sharing the sidebar / topbar / status bar.
 */
export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/login");
  return <>{children}</>;
}
