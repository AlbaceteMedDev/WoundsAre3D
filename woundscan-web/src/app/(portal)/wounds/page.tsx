import Link from "next/link";
import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { PATIENTS } from "@/lib/sample";
import { fmtDate } from "@/lib/format";

export default async function WoundsPage() {
  const session = await getSession();
  return (
    <AppShell
      title="3D Wound Analysis"
      subtitle="High-resolution 3D reconstruction and quantitative analysis"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
        <Tab active>All wounds</Tab>
        <Tab>Active ({PATIENTS.filter((p) => p.status === "active").length})</Tab>
        <Tab>Stalled (3)</Tab>
        <Tab>High-risk ({PATIENTS.filter((p) => p.status === "high-risk").length})</Tab>
        <span className="ml-auto text-ink-muted">Click a wound to open 3D analysis</span>
      </div>

      <div className="card overflow-hidden">
        <table className="table-base">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Wound</th>
              <th>Last capture</th>
              <th className="text-right">Area (cm²)</th>
              <th className="text-right">Volume (cm³)</th>
              <th className="text-right">Healing</th>
              <th>Quality</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {PATIENTS.slice(0, 10).map((p, i) => (
              <tr key={p.id} className="hover:bg-surface-2">
                <td>
                  <div className="font-medium text-ink">{p.name}</div>
                  <div className="text-[11px] text-ink-muted">{p.mrn}</div>
                </td>
                <td className="max-w-[220px] truncate" title={p.primaryDx}>
                  {p.primaryDx}
                </td>
                <td className="whitespace-nowrap text-ink-muted">{fmtDate(p.lastSeen)}</td>
                <td className="text-right tabular-nums">{(18 + i * 1.7).toFixed(1)}</td>
                <td className="text-right tabular-nums">{(6 + i * 0.4).toFixed(1)}</td>
                <td className="text-right">
                  <Bar pct={p.healingPct} />
                </td>
                <td>
                  <span className={`pill ${i % 4 === 0 ? "pill-warn" : "pill-success"}`}>
                    {i % 4 === 0 ? "B" : "A"}
                  </span>
                </td>
                <td>
                  <Link
                    href={`/wounds/${p.id === "p1" ? "abc12345-1234-1234-1234-123456789012" : p.id}/mesh`}
                    className="text-accent hover:text-accent-bright"
                  >
                    Open 3D →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}

function Tab({ children, active }: { children: React.ReactNode; active?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-medium ${
        active ? "bg-accent/15 text-accent" : "border border-hairline text-ink-soft"
      }`}
    >
      {children}
    </span>
  );
}

function Bar({ pct }: { pct: number }) {
  const tone = pct >= 70 ? "success" : pct >= 35 ? "accent" : "warn";
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full" style={{ width: `${pct}%`, background: `rgb(var(--${tone}))` }} />
      </div>
      <span className="font-mono text-[11px] text-ink-soft">{pct}%</span>
    </div>
  );
}
