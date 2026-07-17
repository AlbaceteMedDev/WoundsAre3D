# StrataMetric AI — Web

Next.js 14 app serving two surfaces:

1. **Public marketing site** (`/`) — interactive introduction to
   StrataMetric AI by Albacete MedDev: animated 3D LiDAR hero, the
   capture→report pipeline walkthrough, an interactive sample
   measurement report, the live portal mesh viewer, AWS architecture,
   and compliance posture. Signed-in users skip straight to the portal.
2. **Provider portal** (auth-gated) — clinicians and admins review
   measurements, view trajectories, manage products, audit logs, and
   track ML/phantom drift.

## Deploy (Vercel)

- **Root Directory**: `woundscan-web` (monorepo — set this in the Vercel
  project settings)
- Framework preset: Next.js (auto-detected); no extra env needed for the
  marketing site. Portal API calls expect `API_URL` /
  `NEXT_PUBLIC_API_URL` to point at the measurement engine.
- Custom domain: add `stratametricai.com` (+ `www`) under Project →
  Settings → Domains and point the registrar's DNS at Vercel
  (A `76.76.21.21` / CNAME `cname.vercel-dns.com`).

## Features

- **Auth**: password + TOTP, JWT in HTTP-only cookie
- **Dashboard**: KPI cards, recent measurements feed
- **Wounds**: list, filter, detail page with trajectory charts
- **Phantom**: monthly calibration submission
- **Admin**:
  - Product database management
  - Audit log viewer (tamper-evident hash chain)
  - ML model performance + drift alerts

## Run

```bash
npm install
npm run dev
```

The dashboard expects the engine API at `http://localhost:8000` (override
with `API_URL` for SSR fetches and `NEXT_PUBLIC_API_URL` for client).

## Build

```bash
npm run typecheck
npm run lint
npm run build
```

## Architecture

- App Router (Next.js 14)
- Server Components for SSR pages; Client Components for interactive UI
- Tailwind CSS for styling
- Recharts for trajectories
- Zod for runtime API response validation
- HTTP-only cookies for auth (token never exposed to client JS)
- All requests to engine API are proxied through Next.js API routes so
  that secrets and tokens stay server-side
