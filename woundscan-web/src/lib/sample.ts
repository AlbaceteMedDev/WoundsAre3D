/**
 * Demo data for the portal until the engine endpoints are wired up.
 * Used only by `(portal)/*` pages to populate the UI; nothing here
 * should leak into the real-data path.
 */

export type Patient = {
  id: string;
  name: string;
  mrn: string;
  age: number;
  sex: "F" | "M";
  primaryDx: string;
  woundCount: number;
  lastSeen: string;
  status: "active" | "remission" | "discharged" | "high-risk";
  clinician: string;
  location: string;
  healingPct: number;
};

export const PATIENTS: Patient[] = [
  { id: "p1", name: "Patricia Johnson", mrn: "MRN-002847", age: 67, sex: "F", primaryDx: "Diabetic foot ulcer (R, plantar)", woundCount: 1, lastSeen: "2026-04-29", status: "active", clinician: "Dr. Morgan", location: "Midtown clinic", healingPct: 38 },
  { id: "p2", name: "Robert Williams", mrn: "MRN-002791", age: 73, sex: "M", primaryDx: "Venous leg ulcer (L)", woundCount: 2, lastSeen: "2026-04-28", status: "active", clinician: "Dr. Romero", location: "Westside clinic", healingPct: 62 },
  { id: "p3", name: "Margaret Chen", mrn: "MRN-002836", age: 81, sex: "F", primaryDx: "Pressure injury, sacral, stage 3", woundCount: 1, lastSeen: "2026-04-30", status: "high-risk", clinician: "NP Adler", location: "Bayonne clinic", healingPct: 12 },
  { id: "p4", name: "James Carter", mrn: "MRN-002708", age: 58, sex: "M", primaryDx: "Surgical dehiscence, abdominal", woundCount: 1, lastSeen: "2026-04-25", status: "active", clinician: "Dr. Morgan", location: "Midtown clinic", healingPct: 71 },
  { id: "p5", name: "Linda Hayes", mrn: "MRN-002820", age: 64, sex: "F", primaryDx: "Arterial ulcer, R foot", woundCount: 1, lastSeen: "2026-04-22", status: "high-risk", clinician: "Dr. Romero", location: "Westside clinic", healingPct: 8 },
  { id: "p6", name: "Andrew Kowalski", mrn: "MRN-002612", age: 49, sex: "M", primaryDx: "Trauma, motor-vehicle", woundCount: 1, lastSeen: "2026-04-18", status: "remission", clinician: "NP Adler", location: "Midtown clinic", healingPct: 92 },
  { id: "p7", name: "Sandra Cole", mrn: "MRN-002558", age: 70, sex: "F", primaryDx: "DFU, L plantar 1st MTP", woundCount: 2, lastSeen: "2026-04-30", status: "active", clinician: "Dr. Morgan", location: "Midtown clinic", healingPct: 44 },
  { id: "p8", name: "Carlos Reyes", mrn: "MRN-002701", age: 62, sex: "M", primaryDx: "VLU, gaiter region", woundCount: 1, lastSeen: "2026-04-21", status: "active", clinician: "Dr. Romero", location: "Bayonne clinic", healingPct: 58 },
  { id: "p9", name: "Helen Park", mrn: "MRN-002774", age: 78, sex: "F", primaryDx: "Pressure injury, heel, stage 2", woundCount: 1, lastSeen: "2026-04-23", status: "active", clinician: "NP Adler", location: "Westside clinic", healingPct: 49 },
  { id: "p10", name: "Thomas Briggs", mrn: "MRN-002845", age: 55, sex: "M", primaryDx: "DFU, R hallux", woundCount: 1, lastSeen: "2026-04-29", status: "active", clinician: "Dr. Morgan", location: "Midtown clinic", healingPct: 33 },
  { id: "p11", name: "Olivia Bennett", mrn: "MRN-002690", age: 41, sex: "F", primaryDx: "Burn, lower extremity", woundCount: 1, lastSeen: "2026-04-19", status: "remission", clinician: "Dr. Romero", location: "Westside clinic", healingPct: 88 },
  { id: "p12", name: "Walter Klein", mrn: "MRN-002488", age: 84, sex: "M", primaryDx: "VLU, L medial malleolus", woundCount: 1, lastSeen: "2026-04-15", status: "discharged", clinician: "NP Adler", location: "Bayonne clinic", healingPct: 100 },
];

export type Order = {
  id: string;
  date: string;
  patient: string;
  product: string;
  units: number;
  amount: number;
  status: "shipped" | "delivered" | "in-transit" | "approved" | "review";
  tracking?: string;
};

export const ORDERS: Order[] = [
  { id: "AO-291", date: "2026-04-30", patient: "Patricia Johnson",  product: "ActiGraft+ 4×4 cm", units: 1, amount: 1245.00, status: "shipped",    tracking: "9400-1112-0253" },
  { id: "AO-290", date: "2026-04-30", patient: "Robert Williams",   product: "Collagen wound matrix 4×4", units: 2, amount: 412.50,  status: "delivered" },
  { id: "AO-289", date: "2026-04-29", patient: "James Carter",      product: "UltraMist therapy session", units: 1, amount: 365.00,  status: "approved" },
  { id: "AO-288", date: "2026-04-29", patient: "Margaret Chen",     product: "MicroDoc NPWT canister",   units: 4, amount: 198.40,  status: "in-transit" },
  { id: "AO-287", date: "2026-04-28", patient: "Sandra Cole",       product: "Adhesion barrier 5×5",     units: 1, amount: 1690.00, status: "review" },
  { id: "AO-286", date: "2026-04-28", patient: "Carlos Reyes",      product: "Compression wrap (3 layer)",units: 6,amount: 87.30,   status: "delivered" },
  { id: "AO-285", date: "2026-04-26", patient: "Linda Hayes",       product: "Exosome serum 0.5ml",      units: 1, amount: 2150.00, status: "shipped",    tracking: "9400-1112-0244" },
  { id: "AO-284", date: "2026-04-25", patient: "Helen Park",        product: "Foam dressing 4×4 (10pk)", units: 1, amount: 64.50,   status: "delivered" },
];

export type Claim = {
  id: string;
  patient: string;
  cpt: string;
  amount: number;
  paid: number | null;
  submitted: string;
  adjudicated?: string;
  status: "paid" | "pending" | "denied" | "appeal";
  payer: string;
};

export const CLAIMS: Claim[] = [
  { id: "CLM-2026-00517", patient: "Patricia Johnson", cpt: "15271", amount: 1840.00, paid: 1727.65, submitted: "2026-04-09", adjudicated: "2026-04-22", status: "paid",   payer: "Medicare A/B" },
  { id: "CLM-2026-00516", patient: "Robert Williams",  cpt: "15275", amount: 2100.00, paid: 1965.00, submitted: "2026-04-09", adjudicated: "2026-04-21", status: "paid",   payer: "Aetna" },
  { id: "CLM-2026-00515", patient: "James Carter",     cpt: "97607", amount: 365.00,  paid: null,    submitted: "2026-04-12", status: "pending", payer: "BCBS" },
  { id: "CLM-2026-00514", patient: "Margaret Chen",    cpt: "97606", amount: 412.00,  paid: null,    submitted: "2026-04-14", status: "pending", payer: "Medicare A/B" },
  { id: "CLM-2026-00513", patient: "Sandra Cole",      cpt: "15272", amount: 920.00,  paid: 0,       submitted: "2026-04-04", adjudicated: "2026-04-18", status: "denied", payer: "United" },
  { id: "CLM-2026-00512", patient: "Linda Hayes",      cpt: "15275", amount: 2200.00, paid: null,    submitted: "2026-04-12", status: "appeal",  payer: "Cigna" },
  { id: "CLM-2026-00511", patient: "Carlos Reyes",     cpt: "29581", amount: 145.00,  paid: 145.00,  submitted: "2026-04-02", adjudicated: "2026-04-17", status: "paid",   payer: "Medicare A/B" },
];

export const HEALING_TREND = [
  { week: "W12", target: 1.6, actual: 1.4 },
  { week: "W13", target: 1.6, actual: 1.7 },
  { week: "W14", target: 1.6, actual: 1.9 },
  { week: "W15", target: 1.6, actual: 1.8 },
  { week: "W16", target: 1.6, actual: 2.1 },
  { week: "W17", target: 1.6, actual: 2.4 },
  { week: "W18", target: 1.6, actual: 2.2 },
  { week: "W19", target: 1.6, actual: 2.6 },
];

export const VOLUME_TREND = [
  { day: "Mon", scans: 8 },
  { day: "Tue", scans: 12 },
  { day: "Wed", scans: 14 },
  { day: "Thu", scans: 11 },
  { day: "Fri", scans: 16 },
  { day: "Sat", scans: 4 },
  { day: "Sun", scans: 2 },
];

export const REIMBURSEMENT_TREND = [
  { mo: "Nov", paid: 192_400 },
  { mo: "Dec", paid: 218_900 },
  { mo: "Jan", paid: 241_500 },
  { mo: "Feb", paid: 263_200 },
  { mo: "Mar", paid: 298_700 },
  { mo: "Apr", paid: 337_120 },
];

export const ACTIVITY = [
  { at: "08:42", who: "Dr. Morgan",    what: "Signed progression note", subject: "Patricia Johnson · visit 6" },
  { at: "08:28", who: "NP Adler",      what: "Captured 3D scan",        subject: "Margaret Chen · sacral PI" },
  { at: "08:11", who: "Billing bot",   what: "Submitted claim",         subject: "CLM-2026-00517" },
  { at: "07:55", who: "Dr. Romero",    what: "Approved order",          subject: "AO-291 · ActiGraft+ 4×4" },
  { at: "07:40", who: "Audit log",     what: "Compliance pass",         subject: "Q-code A2005 verified" },
  { at: "07:14", who: "Dr. Morgan",    what: "Updated care plan",       subject: "Sandra Cole · L plantar" },
];
