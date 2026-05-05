import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";

export default async function SettingsPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Settings"
      subtitle="Organization profile · roles · integrations · note templates"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <div className="mb-4 flex flex-wrap gap-1.5 text-xs">
        {["Organization", "Locations", "Clinicians", "Integrations", "Note templates", "Security", "Account"].map(
          (t, i) => (
            <span
              key={t}
              className={`inline-flex items-center rounded-full px-3 py-1.5 font-medium ${
                i === 0 ? "bg-accent/15 text-accent" : "border border-hairline text-ink-soft"
              }`}
            >
              {t}
            </span>
          ),
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Organization profile">
          <Field label="Practice name" value="Albacete Wound Care" />
          <Field label="NPI (Type 2)" value="1467890253" mono />
          <Field label="Tax ID" value="82-2310455" mono />
          <Field label="Primary contact" value="Dr. Rachel Morgan, DPM" />
          <Field label="Email" value="ops@albacetemeddev.com" />
          <Field label="Phone" value="(551) 497-3428" mono />
        </Card>

        <Card title="Clinic locations">
          <Location name="Midtown clinic"  addr="240 W 38th St, NYC NY 10018"   pos="11" beds={6} status="primary" />
          <Location name="Westside clinic" addr="1410 W 80th St, NYC NY 10024"  pos="11" beds={4} status="active" />
          <Location name="Bayonne clinic"  addr="510 Broadway, Bayonne NJ 07002" pos="11" beds={3} status="active" />
          <button className="btn btn-secondary mt-2 w-full justify-center">+ Add location</button>
        </Card>

        <Card title="Clinician roles & permissions">
          <Permission who="Dr. Rachel Morgan, DPM"   role="Admin / clinician"     scope="all locations" />
          <Permission who="Dr. Daniel Romero, DPM"   role="Clinician"             scope="Westside, Bayonne" />
          <Permission who="Karen Adler, NP"          role="Clinician"             scope="Bayonne" />
          <Permission who="Marcus Lee"               role="Billing"               scope="all locations" />
          <Permission who="Audit Bot v3"             role="Read-only auditor"     scope="all locations" />
        </Card>

        <Card title="Notification settings">
          <Toggle label="High-risk patient alerts" on />
          <Toggle label="Stalled wound after 21d" on />
          <Toggle label="Order delivery confirmation" on />
          <Toggle label="Claim adjudicated" on />
          <Toggle label="Compliance exception" on />
          <Toggle label="Weekly digest" />
        </Card>

        <Card title="Integrations">
          <Integration name="AcuityMD"          state="connected" detail="Revenue cycle · synced 2m ago" />
          <Integration name="Availity"          state="connected" detail="Eligibility / 270-271" />
          <Integration name="Change Healthcare" state="connected" detail="837P / 835 / payers" />
          <Integration name="DrFirst"           state="connected" detail="ePrescribing / EPCS" />
          <Integration name="Athena (EHR)"      state="pending"   detail="OAuth handshake pending" />
          <Integration name="DocuSign"          state="optional"  detail="Patient consent capture" />
        </Card>

        <Card title="Note templates">
          <TemplateRow name="HPI Capture" version="v3.2" updated="Apr 18" />
          <TemplateRow name="Tissue Composition" version="v4.1" updated="Apr 22" />
          <TemplateRow name="Reimbursement Justification" version="v2.7" updated="Apr 09" />
          <TemplateRow name="Procedure: Graft Application" version="v3.0" updated="Apr 02" />
          <TemplateRow name="Adverse Event Report" version="v1.4" updated="Mar 18" />
          <button className="btn btn-secondary mt-2 w-full justify-center">+ New template</button>
        </Card>

        <Card title="Security">
          <Field label="MFA" value="Required (TOTP, FIDO2)" />
          <Field label="Session timeout" value="15 minutes idle" />
          <Field label="IP allow-list" value="2 networks" />
          <Field label="Last password rotation" value="Apr 02, 2026" />
          <Field label="Encryption" value="AES-256 at rest, TLS 1.3 in transit" />
        </Card>

        <Card title="HIPAA / audit">
          <Field label="BAA on file" value="signed Jan 14, 2026" />
          <Field label="Audit retention" value="7 years (immutable)" />
          <Field label="Last 3rd-party audit" value="SOC 2 Type II · Q1 2026" />
          <Field label="Audit log volume (mo)" value="48,712 events" />
        </Card>

        <Card title="Data retention">
          <Field label="Measurements" value="7 years (HIPAA min)" />
          <Field label="3D mesh artifacts" value="3 years" />
          <Field label="Photos" value="7 years" />
          <Field label="Derived analytics" value="indefinite (de-identified)" />
        </Card>

        <Card title="Account preferences">
          <Field label="Default view" value="Dashboard" />
          <Field label="Time zone" value="America/New_York" />
          <Field label="Units" value="Metric (cm, cm³)" />
          <Field label="Theme" value="System (light + dark)" />
        </Card>
      </div>
    </AppShell>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card flex flex-col gap-2 p-4">
      <h2 className="font-display text-base font-semibold text-ink">{title}</h2>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between border-b border-hairline pb-1.5 text-sm last:border-b-0 last:pb-0">
      <span className="text-ink-muted">{label}</span>
      <span className={`text-ink ${mono ? "font-mono text-xs" : ""}`}>{value}</span>
    </div>
  );
}

function Location({ name, addr, pos, beds, status }: { name: string; addr: string; pos: string; beds: number; status: "primary" | "active" }) {
  return (
    <div className="rounded-md border border-hairline bg-surface p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-ink">{name}</span>
        <span className={`pill ${status === "primary" ? "pill-accent" : "pill-success"}`}>
          {status}
        </span>
      </div>
      <p className="mt-0.5 text-xs text-ink-muted">{addr}</p>
      <p className="mt-1 text-[11px] text-ink-muted">POS {pos} · {beds} beds</p>
    </div>
  );
}

function Permission({ who, role, scope }: { who: string; role: string; scope: string }) {
  return (
    <div className="rounded-md border border-hairline bg-surface p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-ink">{who}</span>
        <span className="pill pill-accent">{role}</span>
      </div>
      <p className="mt-0.5 text-xs text-ink-muted">scope: {scope}</p>
    </div>
  );
}

function Toggle({ label, on }: { label: string; on?: boolean }) {
  return (
    <label className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2 text-sm">
      <span className="text-ink-soft">{label}</span>
      <span
        className={`flex h-5 w-9 items-center rounded-full px-0.5 transition ${
          on ? "bg-accent" : "bg-hairline"
        }`}
      >
        <span
          className={`h-4 w-4 rounded-full bg-white shadow transition ${on ? "ml-auto" : ""}`}
        />
      </span>
    </label>
  );
}

function Integration({ name, state, detail }: { name: string; state: "connected" | "pending" | "optional"; detail: string }) {
  return (
    <div className="rounded-md border border-hairline bg-surface p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-ink">{name}</span>
        <span
          className={`pill ${
            state === "connected" ? "pill-success" : state === "pending" ? "pill-warn" : "pill-neutral"
          }`}
        >
          {state}
        </span>
      </div>
      <p className="mt-0.5 text-xs text-ink-muted">{detail}</p>
    </div>
  );
}

function TemplateRow({ name, version, updated }: { name: string; version: string; updated: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2 text-sm">
      <span className="text-ink">{name}</span>
      <span className="text-xs text-ink-muted">
        <span className="font-mono">{version}</span> · {updated}
      </span>
    </div>
  );
}
