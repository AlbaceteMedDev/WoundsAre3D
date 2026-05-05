"use client";

import { useState } from "react";
import {
  ANATOMIC_REGIONS,
  PLACE_OF_SERVICE,
  type ReimbursementOut,
} from "@/lib/api";
import { money } from "@/lib/format";

type Props = {
  /** Latest measured surface area; pre-fills applied area when available. */
  defaultAppliedAreaCm2?: number;
  /** Most recent graft package size, if any. */
  defaultPackageSizeCm2?: number;
};

export function ReimbursementPanel({
  defaultAppliedAreaCm2,
  defaultPackageSizeCm2,
}: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ReimbursementOut | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const appliedDefault = defaultAppliedAreaCm2 ? defaultAppliedAreaCm2.toFixed(1) : "";
  const pkgDefault = defaultPackageSizeCm2 ? defaultPackageSizeCm2.toFixed(1) : "";

  async function submit(form: FormData) {
    setSubmitting(true);
    setErr(null);
    setResult(null);
    try {
      const pkg = form.get("package_size_cm2");
      const body = {
        applied_area_cm2: Number(form.get("applied_area_cm2")),
        anatomic_region: String(form.get("anatomic_region")),
        pos_code: String(form.get("pos_code")),
        package_size_cm2: pkg ? Number(pkg) : null,
        drug_asp_per_cm2: Number(form.get("drug_asp_per_cm2") || 0),
        gpci_work: Number(form.get("gpci_work") || 1),
        gpci_pe: Number(form.get("gpci_pe") || 1),
        gpci_mp: Number(form.get("gpci_mp") || 1),
      };
      const res = await fetch("/api/proxy/reimbursement/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      setResult(await res.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card mt-8">
      <header className="card-header">
        <div>
          <h2 className="card-title">Reimbursement estimate</h2>
          <p className="card-subtitle">
            Medicare allowed amount based on CMS PFS RVUs, locality GPCI, POS, and drug Q-code ASP.
            Estimate only — verify on remittance.
          </p>
        </div>
      </header>
      <form action={submit} className="grid grid-cols-1 gap-3 p-4 md:grid-cols-3">
        <Field
          name="applied_area_cm2"
          label="Applied area (cm²)"
          type="number"
          step="0.1"
          required
          defaultValue={appliedDefault || undefined}
          placeholder={appliedDefault ? undefined : "e.g. 12.5"}
          hint={defaultAppliedAreaCm2 ? "Pre-filled from latest measurement." : undefined}
        />
        <Field
          name="package_size_cm2"
          label="Package size (cm²)"
          type="number"
          step="0.1"
          defaultValue={pkgDefault || undefined}
          placeholder={pkgDefault ? undefined : "e.g. 16.0"}
          hint={
            defaultPackageSizeCm2
              ? "Pre-filled from most recent graft."
              : "Leave blank for as-applied billing."
          }
        />
        <Select
          name="anatomic_region"
          label="Anatomic region"
          defaultValue="trunk_arms_legs"
          options={ANATOMIC_REGIONS.map((r) => ({
            value: r.value,
            label: `${r.label} (${r.cpts})`,
          }))}
        />
        <Select
          name="pos_code"
          label="Place of service"
          defaultValue="11"
          options={PLACE_OF_SERVICE.map((o) => ({ value: o.code, label: `${o.code} — ${o.label}` }))}
        />
        <Field name="drug_asp_per_cm2" label="Drug ASP+6% / cm² ($)" type="number" step="0.01" defaultValue="0" />
        <div className="hidden md:block" />
        <Field name="gpci_work" label="GPCI Work" type="number" step="0.0001" defaultValue="1.0" />
        <Field name="gpci_pe" label="GPCI Practice Expense" type="number" step="0.0001" defaultValue="1.0" />
        <Field name="gpci_mp" label="GPCI Malpractice" type="number" step="0.0001" defaultValue="1.0" />
        <div className="md:col-span-3 flex justify-end">
          <button type="submit" disabled={submitting} className="btn btn-primary">
            {submitting ? "Calculating…" : "Calculate"}
          </button>
        </div>
      </form>

      {err && <p className="px-4 pb-4 text-sm text-danger">{err}</p>}

      {result && (
        <div className="border-t border-hairline bg-surface-2 p-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label="Primary CPT" value={result.primary_cpt} sub={money(result.primary_cpt_payment)} />
            <Stat
              label={`Add-on (${result.additional_cpt_units}u)`}
              value={result.additional_cpt_units > 0 ? "billed" : "—"}
              sub={money(result.additional_units_payment)}
            />
            <Stat label="Drug Q-code" value="ASP + 6%" sub={money(result.drug_payment)} />
            <Stat label="Total allowed" value={money(result.total_payment)} accent />
          </div>
          {result.notes.length > 0 && (
            <ul className="mt-4 space-y-1 text-xs text-ink-muted">
              {result.notes.map((n, i) => (
                <li key={i}>• {n}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-md border p-3 ${
        accent
          ? "border-accent bg-accent/10"
          : "border-hairline bg-surface"
      }`}
    >
      <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">{label}</p>
      <p className={`mt-1 font-display text-lg font-semibold ${accent ? "text-accent" : "text-ink"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-ink-muted">{sub}</p>}
    </div>
  );
}

function Field({
  name,
  label,
  type = "text",
  step,
  required,
  defaultValue,
  placeholder,
  hint,
}: {
  name: string;
  label: string;
  type?: string;
  step?: string;
  required?: boolean;
  defaultValue?: string;
  placeholder?: string;
  hint?: string;
}) {
  return (
    <label className="block text-sm">
      <span className="label">{label}</span>
      <input
        name={name}
        type={type}
        step={step}
        required={required}
        defaultValue={defaultValue}
        placeholder={placeholder}
        className="input"
      />
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

function Select({
  name,
  label,
  options,
  defaultValue,
}: {
  name: string;
  label: string;
  options: ReadonlyArray<{ value: string; label: string }>;
  defaultValue?: string;
}) {
  return (
    <label className="block text-sm">
      <span className="label">{label}</span>
      <select name={name} defaultValue={defaultValue} className="input">
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
