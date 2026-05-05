"use client";

import { useMemo, useState } from "react";
import {
  ANATOMIC_REGIONS,
  PLACE_OF_SERVICE,
  TISSUE_CHANNELS,
  WOUND_TYPES,
  type NoteOut,
  type ProgressionPoint,
} from "@/lib/api";
import { fmtDateTime } from "@/lib/format";

type Props = {
  woundId: string;
  patientToken: string;
  measurements: ProgressionPoint[];
  initial: NoteOut[];
};

type WoundType = (typeof WOUND_TYPES)[number];
type TissueChannel = (typeof TISSUE_CHANNELS)[number];

const WOUND_TYPE_LABELS: Record<WoundType, string> = {
  diabetic_foot_ulcer: "Diabetic foot ulcer",
  venous_leg_ulcer: "Venous leg ulcer",
  arterial_ulcer: "Arterial ulcer",
  pressure_injury: "Pressure injury",
  surgical_dehiscence: "Surgical dehiscence",
  trauma: "Trauma",
  burn: "Burn",
  other: "Other",
};

const DRAINAGE_AMOUNT = ["none", "scant", "small", "moderate", "large", "copious"] as const;
const DRAINAGE_QUALITY = ["serous", "serosanguinous", "sanguinous", "purulent", "seropurulent"] as const;
const PERIWOUND = ["intact", "macerated", "erythematous", "indurated", "denuded", "callused"] as const;

/**
 * Wound progression note: clinician records subjective findings against an
 * objective measurement, server generates the templated body, clinician
 * signs. Once signed, edits become amendments — never overwrite.
 */
export function NotesPanel({ patientToken, measurements, initial }: Props) {
  const [items, setItems] = useState<NoteOut[]>(initial);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<NoteOut | null>(null);
  const latest = measurements[0];

  return (
    <section className="card mt-8">
      <header className="card-header">
        <div>
          <h2 className="card-title">Progression notes</h2>
          <p className="card-subtitle">
            Subjective + objective + reimbursement, hashed at sign time for audit.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary disabled:opacity-50"
          onClick={() => setOpen((o) => !o)}
          disabled={!latest}
          title={latest ? "" : "At least one measurement is required"}
        >
          {open ? "Cancel" : "New note"}
        </button>
      </header>

      {open && (
        <NoteForm
          patientToken={patientToken}
          measurements={measurements}
          onCreated={(n) => {
            setItems((prev) => [n, ...prev]);
            setPending(n);
            setOpen(false);
          }}
        />
      )}

      {pending && !pending.is_signed && (
        <SignBanner
          note={pending}
          onSigned={(signed) => {
            setItems((prev) => prev.map((n) => (n.id === signed.id ? signed : n)));
            setPending(null);
          }}
          onDismiss={() => setPending(null)}
        />
      )}

      {items.length === 0 ? (
        <p className="p-6 text-sm text-ink-muted">
          No notes yet. {latest ? "Click New note to draft one." : "Capture a measurement first."}
        </p>
      ) : (
        <ul className="divide-y divide-hairline">
          {items.map((n) => (
            <NoteRow
              key={n.id}
              note={n}
              onSigned={(signed) =>
                setItems((prev) => prev.map((x) => (x.id === signed.id ? signed : x)))
              }
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function NoteRow({ note, onSigned }: { note: NoteOut; onSigned: (n: NoteOut) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [signing, setSigning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function sign() {
    setSigning(true);
    setErr(null);
    try {
      const res = await fetch(`/api/proxy/notes/${note.id}/sign`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      onSigned(await res.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSigning(false);
    }
  }

  return (
    <li className="p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-ink">
            {fmtDateTime(note.authored_at)}
            {note.is_signed && note.signed_at && (
              <span className="pill pill-success ml-2">
                Signed {fmtDateTime(note.signed_at)}
              </span>
            )}
            {!note.is_signed && <span className="pill pill-warn ml-2">Draft</span>}
          </p>
          <p className="mt-1 font-mono text-xs text-ink-muted">
            sha256:{note.body_sha256.slice(0, 16)}… · template {note.template_version}
          </p>
        </div>
        <div className="flex gap-2">
          {!note.is_signed && (
            <button
              type="button"
              onClick={sign}
              disabled={signing}
              className="btn btn-secondary"
            >
              {signing ? "Signing…" : "Sign"}
            </button>
          )}
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="btn btn-secondary"
          >
            {expanded ? "Hide" : "View"}
          </button>
        </div>
      </div>
      {err && <p className="mt-2 text-sm text-danger">{err}</p>}
      {expanded && (
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded border border-hairline bg-surface-2 p-3 font-mono text-xs leading-relaxed text-ink">
          {note.body_text}
        </pre>
      )}
    </li>
  );
}

function SignBanner({
  note,
  onSigned,
  onDismiss,
}: {
  note: NoteOut;
  onSigned: (n: NoteOut) => void;
  onDismiss: () => void;
}) {
  const [signing, setSigning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function sign() {
    setSigning(true);
    setErr(null);
    try {
      const res = await fetch(`/api/proxy/notes/${note.id}/sign`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      onSigned(await res.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setSigning(false);
    }
  }
  return (
    <div className="flex items-center justify-between gap-3 border-b border-warn/30 bg-warn/10 px-4 py-3 text-sm">
      <p className="text-warn">Note drafted. Review the body, then sign to lock the SHA-256.</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onDismiss}
          className="rounded border border-warn/40 px-3 py-1 text-warn hover:bg-warn/15"
        >
          Later
        </button>
        <button
          type="button"
          onClick={sign}
          disabled={signing}
          className="rounded bg-warn px-3 py-1 text-white hover:opacity-90 disabled:opacity-50"
        >
          {signing ? "Signing…" : "Sign now"}
        </button>
      </div>
      {err && <p className="text-sm text-danger">{err}</p>}
    </div>
  );
}

function NoteForm({
  patientToken,
  measurements,
  onCreated,
}: {
  patientToken: string;
  measurements: ProgressionPoint[];
  onCreated: (n: NoteOut) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tissue, setTissue] = useState<Record<TissueChannel, number>>({
    granulation: 70,
    slough: 20,
    eschar: 0,
    epithelial: 10,
  });
  const [includeReimbursement, setIncludeReimbursement] = useState(false);
  const [measurementId, setMeasurementId] = useState(measurements[0]?.measurement_id ?? "");

  const tissueTotal = useMemo(
    () => Object.values(tissue).reduce((a, b) => a + b, 0),
    [tissue],
  );

  const prior = useMemo(() => {
    const idx = measurements.findIndex((m) => m.measurement_id === measurementId);
    return idx >= 0 ? measurements[idx + 1] : undefined;
  }, [measurementId, measurements]);

  async function submit(form: FormData) {
    setSubmitting(true);
    setErr(null);
    try {
      if (Math.abs(tissueTotal - 100) > 1) {
        throw new Error(`Tissue distribution must sum to 100% (currently ${tissueTotal}%).`);
      }
      const tissueFractions: Record<string, number> = Object.fromEntries(
        TISSUE_CHANNELS.map((k) => [k, tissue[k] / 100]),
      );

      const days = (() => {
        if (!prior) return null;
        const cur = measurements.find((m) => m.measurement_id === measurementId);
        if (!cur) return null;
        return Math.max(
          1,
          Math.round(
            (new Date(cur.captured_at).getTime() -
              new Date(prior.captured_at).getTime()) /
              86_400_000,
          ),
        );
      })();

      const body = {
        measurement_id: measurementId,
        anatomic_location: String(form.get("anatomic_location")),
        wound_type: String(form.get("wound_type")),
        patient_token: patientToken,
        tissue_types: tissueFractions,
        drainage_amount: String(form.get("drainage_amount")),
        drainage_quality: String(form.get("drainage_quality")),
        odor: String(form.get("odor")),
        periwound_status: String(form.get("periwound_status")),
        pain_level_0_10: Number(form.get("pain_level_0_10")),
        days_since_prior: days,
        prior_volume_cm3: prior?.volume_cm3 ?? null,
        prior_area_cm2: prior?.surface_area_cm2 ?? null,
        prior_max_depth_cm: prior?.max_depth_cm ?? null,
        clinician_addendum: String(form.get("clinician_addendum") ?? ""),
        reimbursement_hints: includeReimbursement
          ? {
              anatomic_region: String(form.get("anatomic_region")),
              pos_code: String(form.get("pos_code")),
              drug_asp_per_cm2: Number(form.get("drug_asp_per_cm2") ?? 0),
              gpci_work: Number(form.get("gpci_work") ?? 1),
              gpci_pe: Number(form.get("gpci_pe") ?? 1),
              gpci_mp: Number(form.get("gpci_mp") ?? 1),
            }
          : null,
      };
      const res = await fetch("/api/proxy/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      onCreated(await res.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form action={submit} className="space-y-6 border-b border-hairline bg-surface-2 p-4">
      {/* Measurement + identification */}
      <fieldset className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <legend className="col-span-full mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-muted">
          Measurement
        </legend>
        <label className="block text-sm md:col-span-3">
          <span className="label">Captured measurement</span>
          <select
            name="measurement_id"
            value={measurementId}
            onChange={(e) => setMeasurementId(e.target.value)}
            className="input"
            required
          >
            {measurements.map((m) => (
              <option key={m.measurement_id} value={m.measurement_id}>
                {fmtDateTime(m.captured_at)} — {m.surface_area_cm2.toFixed(1)} cm² · vol{" "}
                {m.volume_cm3.toFixed(1)} cm³ · grade {m.quality_grade}
              </option>
            ))}
          </select>
        </label>
        <Field name="anatomic_location" label="Anatomic location" required placeholder="Right plantar 1st MTP" />
        <Select
          name="wound_type"
          label="Wound type"
          options={WOUND_TYPES.map((w) => ({ value: w, label: WOUND_TYPE_LABELS[w] }))}
          defaultValue="diabetic_foot_ulcer"
        />
      </fieldset>

      <fieldset>
        <legend className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-muted">
          Wound bed (must total 100%)
        </legend>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {TISSUE_CHANNELS.map((k) => (
            <label key={k} className="block text-sm">
              <span className="label capitalize">{k}</span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={tissue[k]}
                  onChange={(e) => setTissue((t) => ({ ...t, [k]: Number(e.target.value) || 0 }))}
                  className="input"
                />
                <span className="text-xs text-ink-muted">%</span>
              </div>
            </label>
          ))}
        </div>
        <p
          className={`mt-2 text-xs ${
            Math.abs(tissueTotal - 100) <= 1 ? "text-ink-muted" : "text-danger"
          }`}
        >
          Total: {tissueTotal}%
        </p>
      </fieldset>

      <fieldset className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <legend className="col-span-full mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-muted">
          Drainage &amp; periwound
        </legend>
        <Select
          name="drainage_amount"
          label="Drainage amount"
          options={DRAINAGE_AMOUNT.map((d) => ({ value: d, label: d }))}
          defaultValue="scant"
        />
        <Select
          name="drainage_quality"
          label="Drainage quality"
          options={DRAINAGE_QUALITY.map((d) => ({ value: d, label: d }))}
          defaultValue="serous"
        />
        <Select
          name="odor"
          label="Odor"
          options={["none", "faint", "moderate", "strong"].map((d) => ({ value: d, label: d }))}
          defaultValue="none"
        />
        <Select
          name="periwound_status"
          label="Periwound"
          options={PERIWOUND.map((p) => ({ value: p, label: p }))}
          defaultValue="intact"
        />
        <Field name="pain_level_0_10" label="Pain (0–10)" type="number" defaultValue="0" />
        <Field name="clinician_addendum" label="Addendum (optional)" placeholder="Plan, education, follow-up" />
      </fieldset>

      <fieldset className="rounded border border-dashed border-hairline p-3">
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={includeReimbursement}
            onChange={(e) => setIncludeReimbursement(e.target.checked)}
            className="rounded border-hairline text-accent focus:ring-accent"
          />
          <span>Include Medicare reimbursement estimate (only if grafts were applied this visit)</span>
        </label>
        {includeReimbursement && (
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <Select
              name="anatomic_region"
              label="Anatomic region"
              options={ANATOMIC_REGIONS.map((r) => ({ value: r.value, label: `${r.label} (${r.cpts})` }))}
              defaultValue="trunk_arms_legs"
            />
            <Select
              name="pos_code"
              label="Place of service"
              options={PLACE_OF_SERVICE.map((p) => ({ value: p.code, label: `${p.code} — ${p.label}` }))}
              defaultValue="11"
            />
            <Field name="drug_asp_per_cm2" label="Drug ASP+6% / cm² ($)" type="number" step="0.01" defaultValue="0" />
            <Field name="gpci_work" label="GPCI Work" type="number" step="0.0001" defaultValue="1.0" />
            <Field name="gpci_pe" label="GPCI Practice Expense" type="number" step="0.0001" defaultValue="1.0" />
            <Field name="gpci_mp" label="GPCI Malpractice" type="number" step="0.0001" defaultValue="1.0" />
          </div>
        )}
      </fieldset>

      <div className="flex items-center justify-between gap-2">
        {err && <p className="text-sm text-danger">{err}</p>}
        <button type="submit" disabled={submitting} className="btn btn-primary ml-auto">
          {submitting ? "Generating…" : "Generate draft"}
        </button>
      </div>
    </form>
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
}: {
  name: string;
  label: string;
  type?: string;
  step?: string;
  required?: boolean;
  defaultValue?: string;
  placeholder?: string;
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
