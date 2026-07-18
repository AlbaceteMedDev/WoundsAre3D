import Link from "next/link";
import { WordmarkLockup } from "./Wordmark";

export function Footer() {
  return (
    <footer className="border-t border-hairline bg-surface/60">
      <div className="mk-section grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <WordmarkLockup />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink-muted">
            Objective, reproducible 3D wound measurement from an iPhone LiDAR scan — engineered for
            audit-defensible documentation at the point of care.
          </p>
          <p className="mt-4 font-mono text-[11px] text-ink-muted">stratametricai.com</p>
        </div>

        <nav aria-label="Site">
          <p className="font-display text-sm font-semibold text-ink">Explore</p>
          <ul className="mt-3 space-y-2 text-sm text-ink-soft">
            <li><a className="transition hover:text-accent" href="#technology">Technology</a></li>
            <li><a className="transition hover:text-accent" href="#pipeline">How it works</a></li>
            <li><a className="transition hover:text-accent" href="#report">The report</a></li>
            <li><a className="transition hover:text-accent" href="#demo">Live demo</a></li>
            <li><a className="transition hover:text-accent" href="#portal">Portal tour</a></li>
            <li><a className="transition hover:text-accent" href="#platform">Platform</a></li>
          </ul>
        </nav>

        <nav aria-label="Access">
          <p className="font-display text-sm font-semibold text-ink">Access</p>
          <ul className="mt-3 space-y-2 text-sm text-ink-soft">
            <li><Link className="transition hover:text-accent" href="/login">Portal sign in</Link></li>
            <li><Link className="transition hover:text-accent" href="/demo">3D viewer demo</Link></li>
            <li>
              <a className="transition hover:text-accent" href="mailto:gabe@albacetemeddev.com">
                Request access
              </a>
            </li>
            <li>
              <a
                className="transition hover:text-accent"
                href="https://albacetemeddev.com"
                target="_blank"
                rel="noreferrer"
              >
                Albacete MedDev
              </a>
            </li>
          </ul>
        </nav>
      </div>

      <div className="border-t border-hairline">
        <div className="mk-section flex flex-col items-start justify-between gap-3 py-6 md:flex-row md:items-center">
          <p className="text-xs text-ink-muted">
            © {new Date().getFullYear()} Albacete MedDev LLC. AI Wound Scan is a StrataMetric product,
            part of the Albacete MedDev ecosystem.
          </p>
          <p className="max-w-xl text-[11px] leading-relaxed text-ink-muted">
            For clinical decision support only. Not for diagnostic use. Clinician retains decision
            authority. Methodology disclosed in every report.
          </p>
        </div>
      </div>
    </footer>
  );
}
