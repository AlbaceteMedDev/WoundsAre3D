"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Wordmark } from "./Wordmark";

const LINKS = [
  { href: "#technology", label: "Technology" },
  { href: "#pipeline", label: "How it works" },
  { href: "#report", label: "The report" },
  { href: "#demo", label: "Live demo" },
  { href: "#portal", label: "Portal" },
  { href: "#platform", label: "Platform" },
  { href: "#compliance", label: "Compliance" },
];

/**
 * Marketing navigation: glass bar with scroll progress, anchor links,
 * theme toggle, and the portal sign-in CTA.
 */
export function MarketingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [progress, setProgress] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      setScrolled(y > 12);
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? Math.min(1, y / max) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled
          ? "border-b border-hairline bg-bg/80 backdrop-blur-xl"
          : "border-b border-transparent bg-transparent"
      }`}
    >
      {/* Scroll progress hairline */}
      <span
        aria-hidden
        className="absolute bottom-0 left-0 h-[2px] bg-accent transition-[width] duration-150"
        style={{ width: `${progress * 100}%` }}
      />

      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-6 md:px-8">
        <Link href="/" aria-label="StrataMetric AI home" className="shrink-0">
          <Wordmark className="text-lg md:text-xl" />
        </Link>

        <nav className="hidden items-center gap-6 lg:flex" aria-label="Sections">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="font-display text-sm font-medium text-ink-soft transition hover:text-ink"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login" className="btn btn-primary hidden sm:inline-flex">
            Portal sign in
            <span aria-hidden>→</span>
          </Link>
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-md border border-hairline bg-surface text-ink-soft lg:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
              {open ? (
                <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              ) : (
                <path d="M2 4.5h12M2 8h12M2 11.5h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile sheet */}
      {open && (
        <nav
          className="border-t border-hairline bg-bg/95 px-6 py-4 backdrop-blur-xl lg:hidden"
          aria-label="Sections"
        >
          <ul className="space-y-1">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-3 py-2 font-display text-sm font-medium text-ink-soft transition hover:bg-surface hover:text-ink"
                >
                  {l.label}
                </a>
              </li>
            ))}
            <li className="pt-2">
              <Link href="/login" className="btn btn-primary w-full" onClick={() => setOpen(false)}>
                Portal sign in
              </Link>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
