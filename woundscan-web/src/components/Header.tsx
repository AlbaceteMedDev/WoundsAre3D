import Link from "next/link";
import { getSession } from "@/lib/auth";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

export async function Header() {
  const session = await getSession();
  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/60">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-6">
        <Link href={session ? "/dashboard" : "/"} className="flex items-baseline gap-2">
          <span className="font-display text-xl font-bold tracking-tight text-ink">
            Wound<span className="text-accent">Scan</span>
          </span>
          <span className="hidden text-[11px] uppercase tracking-[0.18em] text-ink-muted sm:inline">
            powered by Albacete MedDev
          </span>
        </Link>

        <div className="flex items-center gap-4">
          {session && (
            <nav className="hidden items-center gap-5 text-sm md:flex">
              <NavLink href="/dashboard">Dashboard</NavLink>
              <NavLink href="/wounds">Wounds</NavLink>
              <NavLink href="/phantom">Phantom</NavLink>
              {session.role === "admin" && (
                <>
                  <NavLink href="/admin/products">Products</NavLink>
                  <NavLink href="/admin/audit">Audit</NavLink>
                  <NavLink href="/admin/ml">ML</NavLink>
                </>
              )}
            </nav>
          )}
          <ThemeToggle />
          {session && (
            <Link
              href="/logout"
              className="rounded border border-hairline bg-surface px-3 py-1.5 text-sm text-ink-soft transition hover:border-accent hover:text-accent"
            >
              Sign out
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="font-display text-sm font-medium text-ink-soft transition hover:text-ink"
    >
      {children}
    </Link>
  );
}
