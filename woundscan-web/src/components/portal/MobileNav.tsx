"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type Item = { label: string; href: string };

const NAV: Item[] = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Patient Roster", href: "/patients" },
  { label: "3D Wound Intelligence", href: "/wounds" },
  { label: "Audit-Safe Notes", href: "/notes" },
  { label: "Inventory & Grafts", href: "/inventory" },
  { label: "Route Planner", href: "/routes" },
  { label: "Orders", href: "/orders" },
  { label: "Claims", href: "/claims" },
  { label: "Compliance", href: "/compliance" },
  { label: "Reports", href: "/reports" },
  { label: "Settings", href: "/settings" },
];

/**
 * Hamburger-driven nav drawer that takes over on viewports below `lg`.
 * The desktop sidebar handles the same nav for `lg` and up; this
 * component is hidden there.
 */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close drawer on route change so nav works without a manual close.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Lock body scroll while the drawer is open.
  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open]);

  return (
    <div className="lg:hidden">
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open navigation"
        className="grid h-9 w-9 place-items-center rounded-md border border-hairline bg-surface text-ink-soft transition hover:border-accent hover:text-accent"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      </button>

      {open && (
        <>
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-40 bg-black/60"
            onClick={() => setOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col bg-surface shadow-elevated">
            <div className="flex items-center justify-between border-b border-hairline px-4 py-4">
              <Link href="/dashboard" className="font-display text-lg font-bold text-ink">
                Wound<span className="text-accent">Scan</span>
              </Link>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="grid h-8 w-8 place-items-center rounded-md text-ink-soft hover:text-ink"
              >
                ✕
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto p-2">
              <ul className="space-y-0.5">
                {NAV.map((item) => {
                  const active =
                    pathname === item.href ||
                    (item.href !== "/dashboard" && pathname?.startsWith(item.href + "/")) ||
                    (item.href === "/wounds" && pathname?.startsWith("/wounds"));
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`block rounded-md px-3 py-2.5 text-sm font-medium transition ${
                          active ? "bg-accent/15 text-accent" : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                        }`}
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
            <div className="border-t border-hairline p-3 text-xs text-ink-muted">
              <span className="relative mr-2 inline-flex h-2 w-2">
                <span className="absolute inset-0 animate-ping rounded-full bg-success/60" />
                <span className="relative h-2 w-2 rounded-full bg-success" />
              </span>
              All systems operational
            </div>
          </aside>
        </>
      )}
    </div>
  );
}
