# WoundScan Web Dashboard

Next.js 14 app for clinicians and admins to review measurements, view
trajectories, manage products, audit logs, and track ML/phantom drift.

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
