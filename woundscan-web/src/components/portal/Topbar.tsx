import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { MobileNav } from "@/components/portal/MobileNav";

type Props = {
  title: string;
  subtitle?: string;
  user: { name: string; role: string } | null;
};

export function Topbar({ title, subtitle, user }: Props) {
  return (
    <div className="sticky top-0 z-20 border-b border-hairline bg-bg/85 backdrop-blur supports-[backdrop-filter]:bg-bg/65">
      <div className="flex items-center gap-3 px-4 py-3 md:px-6">
        <MobileNav />
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-base font-semibold text-ink md:text-lg">{title}</h1>
          {subtitle && <p className="hidden truncate text-xs text-ink-muted md:block">{subtitle}</p>}
        </div>

        <label className="relative hidden xl:block">
          <input
            type="search"
            placeholder="Search patients, IDs, orders, notes…"
            className="input w-72 pl-9"
          />
          <span className="pointer-events-none absolute left-2.5 top-2 text-ink-muted">
            <SearchIcon />
          </span>
        </label>

        <select className="input hidden w-40 xl:block" defaultValue="all-locations" aria-label="Location">
          <option value="all-locations">All locations</option>
          <option value="midtown">Midtown clinic</option>
          <option value="westside">Westside clinic</option>
          <option value="bayonne">Bayonne clinic</option>
        </select>

        <select className="input hidden w-40 xl:block" defaultValue="all-clinicians" aria-label="Clinician">
          <option value="all-clinicians">All clinicians</option>
          <option value="dr">Dr. Romero</option>
          <option value="rm">Dr. Morgan</option>
          <option value="ka">NP Adler</option>
        </select>

        <button
          type="button"
          aria-label="Search"
          className="grid h-9 w-9 place-items-center rounded-md border border-hairline bg-surface text-ink-soft xl:hidden"
        >
          <SearchIcon />
        </button>

        <ThemeToggle />

        {user && (
          <div className="flex items-center gap-2 rounded-md border border-hairline bg-surface px-2 py-1.5">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-accent/15 text-[11px] font-bold text-accent">
              {initials(user.name)}
            </span>
            <span className="hidden text-xs leading-tight md:block">
              <span className="block font-medium text-ink">{user.name}</span>
              <span className="text-ink-muted">{user.role}</span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  );
}
