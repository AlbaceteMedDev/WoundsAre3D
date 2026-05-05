"use client";

import { useState } from "react";
import type { GraftApplication } from "@/lib/api";
import { daysUntil, fmtDate } from "@/lib/format";

type Props = {
  woundId: string;
  initial: GraftApplication[];
};

/**
 * Lists all UDI-traceable graft applications on a wound, with a form to
 * record a new one. Captures serial / lot / expiration so audits and
 * recalls can link a specific physical unit to this patient + visit.
 */
export function GraftPanel({ woundId, initial }: Props) {
  const [items, setItems] = useState<GraftApplication[]>(initial);
  const [open, setOpen] = useState(false);

  return (
    <section className="card mt-8">
      <header className="card-header">
        <div>
          <h2 className="card-title">Grafts applied</h2>
          <p className="card-subtitle">
            UDI traceability: serial · lot · expiration recorded for every application.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setOpen((o) => !o)}>
          {open ? "Cancel" : "Record application"}
        </button>
      </header>

      {open && (
        <NewGraftForm
          woundId={woundId}
          onCreated={(g) => {
            setItems((prev) => [g, ...prev]);
            setOpen(false);
          }}
        />
      )}

      {items.length === 0 ? (
        <p className="p-6 text-sm text-ink-muted">No grafts applied yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead>
              <tr>
                <th>Applied</th>
                <th>Product</th>
                <th>Serial</th>
                <th>Lot</th>
                <th>Expiration</th>
                <th className="text-right">Applied / Pkg</th>
                <th className="text-right">Waste</th>
              </tr>
            </thead>
            <tbody>
              {items.map((g) => (
                <tr key={g.id}>
                  <td className="whitespace-nowrap">{fmtDate(g.applied_at)}</td>
                  <td>
                    <div className="font-medium text-ink">{g.product_name}</div>
                    {g.udi_di && (
                      <div className="font-mono text-[11px] text-ink-muted">UDI-DI {g.udi_di}</div>
                    )}
                  </td>
                  <td className="font-mono text-xs">{g.serial_number}</td>
                  <td className="font-mono text-xs">{g.lot_number}</td>
                  <td>
                    <ExpirationBadge date={g.expiration_date} />
                  </td>
                  <td className="text-right tabular-nums">
                    {g.applied_area_cm2.toFixed(1)} / {g.package_size_cm2.toFixed(1)} cm²
                  </td>
                  <td className="text-right tabular-nums text-ink-muted">
                    {g.waste_area_cm2.toFixed(1)} cm²
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ExpirationBadge({ date }: { date: string }) {
  const days = daysUntil(date);
  if (days < 0) return <span className="pill pill-danger">Expired {-days}d ago</span>;
  if (days < 30) return <span className="pill pill-warn">{days}d left</span>;
  return <span className="pill pill-neutral">{fmtDate(date)}</span>;
}

function NewGraftForm({
  woundId,
  onCreated,
}: {
  woundId: string;
  onCreated: (g: GraftApplication) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(form: FormData) {
    setSubmitting(true);
    setErr(null);
    try {
      const body = {
        wound_id: woundId,
        product_id: String(form.get("product_id")),
        product_name: String(form.get("product_name")),
        udi_di: form.get("udi_di") ? String(form.get("udi_di")) : null,
        serial_number: String(form.get("serial_number")),
        lot_number: String(form.get("lot_number")),
        expiration_date: String(form.get("expiration_date")),
        manufacture_date: form.get("manufacture_date")
          ? String(form.get("manufacture_date"))
          : null,
        package_size_cm2: Number(form.get("package_size_cm2")),
        applied_area_cm2: Number(form.get("applied_area_cm2")),
        hcpcs_code: form.get("hcpcs_code") ? String(form.get("hcpcs_code")) : null,
        cpt_code: form.get("cpt_code") ? String(form.get("cpt_code")) : null,
        notes: String(form.get("notes") ?? ""),
      };
      const res = await fetch("/api/proxy/grafts/applications", {
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
    <form
      action={submit}
      className="grid grid-cols-1 gap-3 border-b border-hairline bg-surface-2 p-4 md:grid-cols-3"
    >
      <Field name="product_name" label="Product name" required />
      <Field name="product_id" label="Product code" required />
      <Field name="udi_di" label="UDI-DI (optional)" />
      <Field name="serial_number" label="Serial number" required />
      <Field name="lot_number" label="Lot number" required />
      <Field name="expiration_date" label="Expiration" type="date" required />
      <Field name="manufacture_date" label="Manufactured (optional)" type="date" />
      <Field name="package_size_cm2" label="Package size (cm²)" type="number" step="0.1" required />
      <Field name="applied_area_cm2" label="Applied area (cm²)" type="number" step="0.1" required />
      <Field name="hcpcs_code" label="HCPCS Q-code (optional)" />
      <Field name="cpt_code" label="CPT (optional)" />
      <Field name="notes" label="Notes" />
      <div className="flex items-center justify-between gap-2 md:col-span-3">
        {err && <p className="text-sm text-danger">{err}</p>}
        <button type="submit" disabled={submitting} className="btn btn-primary ml-auto">
          {submitting ? "Saving…" : "Save application"}
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
}: {
  name: string;
  label: string;
  type?: string;
  step?: string;
  required?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="label">{label}</span>
      <input name={name} type={type} step={step} required={required} className="input" />
    </label>
  );
}
