import { Sidebar } from "@/components/portal/Sidebar";
import { Topbar } from "@/components/portal/Topbar";
import { StatusBar } from "@/components/portal/StatusBar";

type Props = {
  title: string;
  subtitle?: string;
  user: { name: string; role: string } | null;
  children: React.ReactNode;
};

export function AppShell({ title, subtitle, user, children }: Props) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} subtitle={subtitle} user={user} />
        <main className="flex-1 px-6 py-6">{children}</main>
        <StatusBar auditCount={142} />
      </div>
    </div>
  );
}
