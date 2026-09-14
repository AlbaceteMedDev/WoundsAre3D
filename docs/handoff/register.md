| # | ID | Severity | Source | Title | Verdict | Est. | Dup of |
|---|---|---|---|---|---|---|---|
| 1 | `contract-env-secrets-F1` | **blocker** | contract-env-secrets | Web login route grants a clinician session to any credentials when the engine is unreachable or WS_DEMO_MODE=1 | confirmed |  | web-portal-G7 |
| 2 | `contract-env-secrets-F2` | **blocker** | contract-env-secrets | WS_JWT_SIGNING_KEY silently defaults to a public string and prod terraform never sets it | confirmed |  | engine-api-auth-storage-G7 |
| 3 | `contract-env-secrets-F3` | **blocker** | contract-env-secrets | Engine has no real credential path; WS_ALLOW_DEV_LOGIN is the only login and its defaults are dev@local/dev/000000 | adjusted |  | engine-api-auth-storage-G1 |
| 4 | `contract-env-secrets-F8` | **blocker** | contract-env-secrets | Prod environment has no ALB, TLS certificate, or domain, so no public API hostname exists for prod | adjusted |  | infra-ci-ops-G1 |
| 5 | `contract-ios-engine-F1` | **blocker** | contract-ios-engine | Engine datetimes carry microseconds; Swift .iso8601 decoder rejects them, so login and measurement responses always fail to decode | adjusted |  | ios-app-G2 |
| 6 | `contract-ios-engine-F2` | **blocker** | contract-ios-engine | Engine /auth/login has no production credential path; only the WS_ALLOW_DEV_LOGIN stub exists | confirmed |  | engine-api-auth-storage-G1 |
| 7 | `contract-ios-engine-F3` | **blocker** | contract-ios-engine | Capture flow never uploads artifacts or creates a measurement; the upload/measurement API surface is dead code | confirmed |  | ios-app-G1 |
| 8 | `contract-ios-engine-F4` | **blocker** | contract-ios-engine | /uploads/presigned returns hard-coded http://localhost:9000 URLs; no presigned-PUT implementation and no ATS exception on iOS | adjusted |  | engine-api-auth-storage-G4 |
| 9 | `contract-regulatory-F1` | **blocker** | contract-regulatory | No physical, phantom, or clinical data exists; production pipeline never ingests LiDAR depth | confirmed |  | engine-core-math-G2 |
| 10 | `contract-regulatory-F10` | **blocker** | contract-regulatory | No design-control, risk-management, IEC 62304, cybersecurity, labeling, or predicate artifacts exist | confirmed |  |  |
| 11 | `contract-regulatory-F2` | **blocker** | contract-regulatory | '±0.3 mm instrument precision @95%' is not derivable from any code or test | adjusted |  | web-marketing-G1 |
| 12 | `contract-regulatory-F7` | **blocker** | contract-regulatory | Deployed copy makes regulatory and technical claims the code contradicts (CDS exemption, SOC 2, SAM, plane fit, no probe) | adjusted |  |  |
| 13 | `contract-security-phi-F1` | **blocker** | contract-security-phi | Web login grants a session for any (or invalid) credentials via demo fallback | confirmed |  | web-portal-G7 |
| 14 | `contract-security-phi-F2` | **blocker** | contract-security-phi | Session cookie is unsigned JSON; role and identity are client-controlled | confirmed |  |  |
| 15 | `contract-security-phi-F4` | **blocker** | contract-security-phi | No tenant scoping on wounds, measurements, mesh, PDF, FHIR, phantom; RBAC unenforced outside admin | confirmed |  | engine-api-auth-storage-G5 |
| 16 | `contract-security-phi-F7` | **blocker** | contract-security-phi | JWT signing key falls back to a public constant and prod terraform does not supply one | confirmed |  | engine-api-auth-storage-G7 |
| 17 | `contract-web-engine-F1` | **blocker** | contract-web-engine | Login fallback grants a session for any credentials on engine error | confirmed |  | web-portal-G7 |
| 18 | `engine-api-auth-storage-G1` | **blocker** | engine-api-auth-storage | No production login path exists - only the env-gated dev backdoor | adjusted | 3-5 days |  |
| 19 | `engine-api-auth-storage-G2` | **blocker** | engine-api-auth-storage | All clinical data lives in per-process Python dicts; Postgres models are never used | confirmed | 1-2 weeks |  |
| 20 | `engine-api-auth-storage-G3` | **blocker** | engine-api-auth-storage | Pipeline ignores uploaded S3 keys and synthesizes camera depth (depth=0) | confirmed | 1-2 weeks (depends on capture/fusion subsystem) | engine-core-math-G2 |
| 21 | `engine-api-auth-storage-G4` | **blocker** | engine-api-auth-storage | /uploads/presigned returns fake http://localhost:9000 URLs; no presigned PUT implementation | adjusted | 1 day |  |
| 22 | `engine-api-auth-storage-G5` | **blocker** | engine-api-auth-storage | No tenant isolation on wounds/measurements/phantom and no RBAC outside /admin | adjusted | 2-3 days |  |
| 23 | `engine-api-auth-storage-G7` | **blocker** | engine-api-auth-storage | JWT signing key silently falls back to a hardcoded constant; prod terraform does not inject one | adjusted | 0.5 day |  |
| 24 | `engine-core-math-G1` | **blocker** | engine-core-math | GP fusion prior is mis-specified (zero mean, fixed 1 mm^2 signal variance, unbounded lengthscale) | adjusted | 1-2 d |  |
| 25 | `engine-core-math-G2` | **blocker** | engine-core-math | No real camera depth reaches the math: pipeline feeds placeholder zero-depth camera anchors and the capture->wound-local projection is absent | adjusted | 1-2 wk |  |
| 26 | `engine-ml-quality-validation-G1` | **blocker** | engine-ml-quality-validation | No trained weights, no loading path, and no ML model is ever invoked by the API | confirmed | (a) 1-2 days; (b) 4-8 weeks incl. data/labelling, plus regulatory validation |  |
| 27 | `engine-output-business-G1` | **blocker** | engine-output-business | All outputs served from process-local dicts; nothing persisted to S3/Postgres despite response claiming a PDF S3 key | confirmed | 3-5 days | engine-api-auth-storage-G2 |
| 28 | `engine-tests-docs-packaging-G1` | **blocker** | engine-tests-docs-packaging | Tier-3 benchmarks and REQ-ACC-005 compare the integrator to itself | adjusted | 1-2 days |  |
| 29 | `engine-tests-docs-packaging-G2` | **blocker** | engine-tests-docs-packaging | Integration suite validates placeholders (in-memory stores, stub presign, zero-depth camera anchors) | adjusted | 3-5 days test work after storage wiring exists |  |
| 30 | `infra-ci-ops-G1` | **blocker** | infra-ci-ops | Prod has no ALB/ACM/HTTPS — API is unreachable from the internet | confirmed | 0.5 day |  |
| 31 | `infra-ci-ops-G2` | **blocker** | infra-ci-ops | Prod ECS task has no environment variables and no JWT secret — engine would talk to localhost DB, wrong S3 bucket, insecure JWT key | confirmed | 0.5 day |  |
| 32 | `infra-ci-ops-G3` | **blocker** | infra-ci-ops | Prod task launch will fail: execution role cannot decrypt the KMS-encrypted DB secret | confirmed | 0.25 day |  |
| 33 | `infra-ci-ops-G4` | **blocker** | infra-ci-ops | Secrets bootstrap is a chicken-and-egg: first apply fails and the RUNBOOK ordering conflicts with Terraform | adjusted | 0.5 day |  |
| 34 | `ios-app-G1` | **blocker** | ios-app | Capture flow never uploads or creates a measurement — dead-ends at UploadingView | confirmed | 3-5 days iOS + engine coordination |  |
| 35 | `ios-app-G15` | **blocker** | ios-app | Portal URL derivation assumes an api. prefix that production does not use | adjusted | 1 hour |  |
| 36 | `ios-app-G2` | **blocker** | ios-app | Login always fails: .iso8601 decoder rejects engine's fractional-second timestamps | confirmed | 1-2 hours |  |
| 37 | `ios-app-G3` | **blocker** | ios-app | Portal SSO broken: ws_session cookie value format does not match the web app | confirmed | 0.5-1 day (both sides) |  |
| 38 | `web-marketing-G1` | **blocker** | web-marketing | Unsupported '±0.3 mm @95%' precision claim on hero, HUD, report and OG image | confirmed | 2-3 hours copy + OG regen |  |
| 39 | `web-portal-G1` | **blocker** | web-portal | /logout throws 500 and no sign-out exists in portal chrome; demo cookie traps users on /dashboard for 12h | adjusted | 1-2 hours |  |
| 40 | `web-portal-G7` | **blocker** | web-portal | Login treats engine 401 and a 1.5s stall identically (demo), engine rejects everything unless WS_ALLOW_DEV_LOGIN=1, and the UI never shows demo mode | confirmed | 2-3 hours |  |
| 41 | `contract-env-secrets-F13` | **major** | contract-env-secrets | CI references no secrets, has no deploy pipeline, the iOS job always no-ops, and security scans are non-blocking | adjusted |  | infra-ci-ops-G10 |
| 42 | `contract-env-secrets-F4` | **major** | contract-env-secrets | iOS API host is hardcoded to the old-brand domain and the WS_API_BASE_URL override is defined nowhere | adjusted |  | ios-app-G14 |
| 43 | `contract-env-secrets-F5` | **major** | contract-env-secrets | Presigned upload endpoint returns http://localhost:9000 placeholders; S3Storage is never wired | adjusted |  | engine-api-auth-storage-G4 |
| 44 | `contract-env-secrets-F6` | **major** | contract-env-secrets | DB/S3/Redis config defaults to localhost and password 'woundscan'; prod terraform overrides none of it and bucket names disagree | confirmed |  | infra-ci-ops-G2 |
| 45 | `contract-env-secrets-F7` | **major** | contract-env-secrets | Secrets Manager wiring is incomplete: db-password secrets have no version, dev jwt secret is a data source, prod has no jwt secret | adjusted |  | infra-ci-ops-G4 |
| 46 | `contract-env-secrets-F9` | **major** | contract-env-secrets | Web API_URL is undefined in every deployment artifact; NEXT_PUBLIC_API_URL feeds dead code | confirmed |  | web-portal-G7 |
| 47 | `contract-ios-engine-F5` | **major** | contract-ios-engine | No wound is ever created or selected on iOS, but wound_id is mandatory on both engine endpoints; the iOS Wound model cannot decode engine WoundOut | confirmed |  | ios-app-G1 |
| 48 | `contract-ios-engine-F6` | **major** | contract-ios-engine | Embedded-portal SSO is broken: ws_session cookie value format does not match the portal, and portalURL resolves to the API host | confirmed |  | ios-app-G3 |
| 49 | `contract-ios-engine-F7` | **major** | contract-ios-engine | 15-minute JWT with no refresh endpoint, no 401 handling on iOS, and logout that neither side actually performs | confirmed |  | engine-api-auth-storage-G6 |
| 50 | `contract-ios-engine-F8` | **major** | contract-ios-engine | Measurement and mesh state lives in per-process dicts while prod runs 2+ ECS replicas; GET after POST can 404 from the app | adjusted |  | engine-api-auth-storage-G2 |
| 51 | `contract-regulatory-F3` | **major** | contract-regulatory | REQ-ACC-005 and all Tier-3 'clinical morphology' benchmarks are tautological (truth = function under test on the same grid) | adjusted |  | engine-tests-docs-packaging-G1 |
| 52 | `contract-regulatory-F4` | **major** | contract-regulatory | Traceability checker verifies only that a test file exists; 'bidirectional' coverage claim is false | adjusted |  | engine-tests-docs-packaging-G3 |
| 53 | `contract-regulatory-F5` | **major** | contract-regulatory | 95% CI calibration is never tested and its inputs are unfitted constants | adjusted |  | engine-tests-docs-packaging-G14 |
| 54 | `contract-regulatory-F6` | **major** | contract-regulatory | PDF report discloses a methodology the production code does not follow and prints fabricated quality sub-scores | confirmed |  | engine-output-business-G6 |
| 55 | `contract-regulatory-F8` | **major** | contract-regulatory | Validation and ML docs describe programs and models that do not exist in code | confirmed |  | engine-tests-docs-packaging-G6 |
| 56 | `contract-regulatory-F9` | **major** | contract-regulatory | Provenance accepts empty model hashes and 'unknown' git SHA silently | adjusted |  | engine-output-business-G7 |
| 57 | `contract-security-phi-F10` | **major** | contract-security-phi | Upload/measurement input surface: placeholder presigned URLs, unvalidated key segments, unbounded payload sizes, synchronous heavy compute | confirmed |  |  |
| 58 | `contract-security-phi-F11` | **major** | contract-security-phi | Prod terraform has no ALB/TLS, no JWT secret, no DB environment, no task S3/KMS policy; cannot serve traffic as written | confirmed |  | infra-ci-ops-G2 |
| 59 | `contract-security-phi-F12` | **major** | contract-security-phi | In-VPC transport not enforced: no RDS force_ssl/sslmode, plaintext Redis for Celery results holding measurement PHI | confirmed |  |  |
| 60 | `contract-security-phi-F13` | **major** | contract-security-phi | Encryption at rest mostly correct, but logs and Performance Insights lack CMK and object lock is GOVERNANCE mode | confirmed |  | infra-ci-ops-G8 |
| 61 | `contract-security-phi-F14` | **major** | contract-security-phi | Backups and detective controls: 7-day RDS retention, no AWS Backup, no CloudTrail, pgaudit preloaded but not configured, hard S3 expiry at 6y | confirmed |  | infra-ci-ops-G8 |
| 62 | `contract-security-phi-F15` | **major** | contract-security-phi | Log redaction is a fixed-key stub that is never called; raw exception text and resource UUIDs reach logs and metrics | confirmed |  | engine-ml-quality-validation-G8 |
| 63 | `contract-security-phi-F16` | **major** | contract-security-phi | Phone-handoff capture API is unauthenticated and stores wound photos + patient labels in Next.js process memory | confirmed |  | web-portal-G4 |
| 64 | `contract-security-phi-F17` | **major** | contract-security-phi | Web proxy is an authenticated open relay to every engine path with no size cap; masks upstream auth failures | confirmed |  | web-portal-G6 |
| 65 | `contract-security-phi-F18` | **major** | contract-security-phi | Web headers: no CSP; Permissions-Policy disables the camera on the app's own capture page; mock PHI-like data rendered on auth failure | adjusted |  | web-portal-G14 |
| 66 | `contract-security-phi-F3` | **major** | contract-security-phi | Engine has no production authentication path; login is a static env-gated dev credential | adjusted |  | engine-api-auth-storage-G1 |
| 67 | `contract-security-phi-F5` | **major** | contract-security-phi | All PHI persistence is in-process dicts; Postgres models, migrations, RLS and column encryption are unwired or absent | adjusted |  | engine-api-auth-storage-G2 |
| 68 | `contract-security-phi-F6` | **major** | contract-security-phi | Audit log is in-memory per process and the tamper-evident chain is never verified or persisted | adjusted |  | engine-api-auth-storage-G8 |
| 69 | `contract-security-phi-F8` | **major** | contract-security-phi | Server-side sessions, logout revocation, idle timeout and MFA are implemented but never invoked | confirmed |  | engine-api-auth-storage-G6 |
| 70 | `contract-security-phi-F9` | **major** | contract-security-phi | Engine API hardening absent: wildcard CORS, public /docs and /metrics leaking resource IDs, no rate limiting, no security headers, no exception handler | confirmed |  |  |
| 71 | `contract-web-engine-F2` | **major** | contract-web-engine | Session cookie is unsigned JSON; role and userId are trusted from the client | confirmed |  | contract-security-phi-F2 |
| 72 | `contract-web-engine-F3` | **major** | contract-web-engine | Progression point ordering contract inverted between engine and web | adjusted |  | web-portal-G3 |
| 73 | `contract-web-engine-F4` | **major** | contract-web-engine | Phone capture handoff is an in-process Map that never reaches the engine and cannot work on Vercel | adjusted |  | web-portal-G4 |
| 74 | `contract-web-engine-F6` | **major** | contract-web-engine | Silent substitution of fabricated clinical data when the engine is absent or errors | confirmed |  | web-portal-G6 |
| 75 | `contract-web-engine-F7` | **major** | contract-web-engine | 12 of 14 portal pages and all admin pages are hardcoded; engine endpoints that could back them are never called | confirmed |  |  |
| 76 | `critic-G1` | **major** | critic | No PHI retention schedule, disposal/deletion or right-to-amend workflow; every S3 object is locked for 6 years and the portal shows a fabricated retention policy | adjusted | 3-5 days engineering after storage wiring, plus policy authoring |  |
| 77 | `critic-G2` | **major** | critic | No backup restore procedure or DR drill; deployment.md asserts cross-region replication, quarterly rehearsal and RTO 4h/RPO 1h that nothing backs | confirmed | 2-3 days |  |
| 78 | `critic-G3` | **major** | critic | No incident-response, HIPAA breach-notification, on-call or SLO definitions; dashboards exist only as prose | confirmed | 2 days |  |
| 79 | `critic-G4` | **major** | critic | No privacy policy, terms of service or BAA pages anywhere on the web app; the portal displays a fabricated 'BAA on file' date | confirmed | 1-2 days engineering; legal drafting external |  |
| 80 | `engine-api-auth-storage-G10` | **major** | engine-api-auth-storage | Datetimes serialize with microseconds; iOS ISO8601 decoder will reject them | confirmed | 0.5 day | ios-app-G2 |
| 81 | `engine-api-auth-storage-G11` | **major** | engine-api-auth-storage | Measurement sign-off changes no state | confirmed | 1 day |  |
| 82 | `engine-api-auth-storage-G12` | **major** | engine-api-auth-storage | PDF/FHIR exports embed placeholder identifiers and are never stored | confirmed | 1-2 days | engine-output-business-G6 |
| 83 | `engine-api-auth-storage-G13` | **major** | engine-api-auth-storage | Schema is unmanaged: no Alembic migrations, no RLS, no column encryption, naive DateTimes, missing tables | confirmed | 3-4 days |  |
| 84 | `engine-api-auth-storage-G6` | **major** | engine-api-auth-storage | Sessions are not server-side: logout is a no-op, no idle refresh, hard 15-minute expiry | confirmed | 2 days |  |
| 85 | `engine-api-auth-storage-G8` | **major** | engine-api-auth-storage | Audit log is in-memory only and its hash chain can never be verified | confirmed | 2-3 days |  |
| 86 | `engine-core-math-G3` (RESOLVED) | **major** | engine-core-math | Undermining volume/surface formulas are physically wrong and the module is unwired; sidewall module absent | confirmed | 1-2 d |  |
| 87 | `engine-core-math-G4` | **major** | engine-core-math | Fiducial scale check is wrong for the documented 4-corner marker layout and unused | adjusted | 2-4 h |  |
| 88 | `engine-core-math-G5` | **major** | engine-core-math | All calibration constants are assumed, not measured, and several are silently hardcoded on the production path | confirmed | 1-2 wk |  |
| 89 | `engine-core-math-G6` | **major** | engine-core-math | Regulatory and benchmark 'ground truth' for irregular and clinical wounds is tautological | confirmed | 4-8 h | engine-tests-docs-packaging-G1 |
| 90 | `engine-core-math-G7` | **major** | engine-core-math | Kalman temporal fusion, bundle adjustment and TPS fallback are implemented but not wired; docs claim otherwise | confirmed | 3-5 d |  |
| 91 | `engine-ml-quality-validation-G2` | **major** | engine-ml-quality-validation | Fallback output is mislabelled with the weights-file name when torch is absent or weights are corrupt | confirmed | 0.5 day |  |
| 92 | `engine-ml-quality-validation-G3` | **major** | engine-ml-quality-validation | Tissue classifier has no ML branch; probe detector is a hard stub | confirmed | 2-4 weeks each with data; 0.5 day to remove | engine-ml-quality-validation-G1 |
| 93 | `engine-ml-quality-validation-G4` | **major** | engine-ml-quality-validation | Per-pixel quality/confidence subsystem is dead code; grade uses hardcoded constants | confirmed | 1-2 weeks (depends on capture ingestion being built) |  |
| 94 | `engine-ml-quality-validation-G5` | **major** | engine-ml-quality-validation | Camera-probe consistency check never runs | confirmed | 2 days once depth ingestion exists |  |
| 95 | `engine-ml-quality-validation-G6` | **major** | engine-ml-quality-validation | Business metrics are declared but never incremented; RUNBOOK alarms reference empty series | confirmed | 1 day |  |
| 96 | `engine-ml-quality-validation-G7` | **major** | engine-ml-quality-validation | Tracing has no exporter and no spans | confirmed | 1 day |  |
| 97 | `engine-ml-quality-validation-G8` | **major** | engine-ml-quality-validation | Error reporter is initialised but never used; exceptions bypass PHI sanitisation | confirmed | 1 day |  |
| 98 | `engine-output-business-G10` | **major** | engine-output-business | Notes auto-generate interpretive clinical trajectory statements with a threshold that contradicts the documented rule | confirmed | 0.5 day plus review |  |
| 99 | `engine-output-business-G2` | **major** | engine-output-business | Medicare estimator is CY2025-only, hardcoded, and structurally wrong for >=100 cm2 wounds and 2026 skin-substitute policy | adjusted | 3-4 days plus an annual update procedure |  |
| 100 | `engine-output-business-G3` | **major** | engine-output-business | Graft product catalog is fictional placeholder data with no UDI/HCPCS/cost and no way to load a real list | confirmed | 2-3 days plus data sourcing |  |
| 101 | `engine-output-business-G4` | **major** | engine-output-business | Pipeline ignores wound indication, selected products, overlap delta and contraindications when recommending grafts | confirmed | 1 day |  |
| 102 | `engine-output-business-G5` | **major** | engine-output-business | Graft area formula double-counts the perimeter offset term | confirmed | 0.5 day plus validation sign-off |  |
| 103 | `engine-output-business-G6` | **major** | engine-output-business | PDF discloses inaccurate methodology and prints provenance as Python repr with hardcoded patient/clinician identifiers | adjusted | 1-2 days |  |
| 104 | `engine-output-business-G7` | **major** | engine-output-business | Provenance record omits raw capture artifacts and carries placeholder git/model identities | confirmed | 2 days (artifact hashing depends on S3 fetch work in the capture/pipeline subsystem) |  |
| 105 | `engine-output-business-G8` | **major** | engine-output-business | FHIR bundle is not a conformant/usable R4 payload | adjusted | 1-2 days |  |
| 106 | `engine-output-business-G9` | **major** | engine-output-business | Note signing is not audit-defensible: in-memory, no signer on the note, no hash re-verification, no amendment, generic audit actions | confirmed | 2 days |  |
| 107 | `engine-tests-docs-packaging-G14` | **major** | engine-tests-docs-packaging | REQ-INV-005 tests point-estimate-in-CI, not truth coverage | adjusted | 1-2 hours |  |
| 108 | `engine-tests-docs-packaging-G3` | **major** | engine-tests-docs-packaging | 'Traced' means only that a test file exists; docs claim bidirectional mapping to passing tests | adjusted | 0.5 day |  |
| 109 | `engine-tests-docs-packaging-G4` | **major** | engine-tests-docs-packaging | Coverage gate sits at exactly 90% with fillers and unmeasured subprocess tests | adjusted | 1 day |  |
| 110 | `engine-tests-docs-packaging-G5` | **major** | engine-tests-docs-packaging | mypy, bandit, pip-audit are non-blocking while docs advertise mypy strict | adjusted | 1-3 days depending on mypy error volume | infra-ci-ops-G10 |
| 111 | `engine-tests-docs-packaging-G6` | **major** | engine-tests-docs-packaging | Docs and README are stale on persistence, async, ML, metrics port, RLS, Alembic, test count | confirmed | 1 day |  |
| 112 | `engine-tests-docs-packaging-G7` | **major** | engine-tests-docs-packaging | Dockerfile runs as root, unpinned, single-stage, ignores uv.lock, no ML extras | confirmed | 0.5-1 day |  |
| 113 | `engine-tests-docs-packaging-G8` | **major** | engine-tests-docs-packaging | docker-compose ships dev secrets and dev-login, and its Postgres/Redis are unused by the app | adjusted | 0.5 day |  |
| 114 | `infra-ci-ops-G10` | **major** | infra-ci-ops | Security/type gates are non-blocking and there is no CD at all | confirmed | 1-2 days |  |
| 115 | `infra-ci-ops-G12` | **major** | infra-ci-ops | Web portal login has an always-on demo bypass — any credentials succeed when the engine is down or rejects them | adjusted | 0.5 day | web-portal-G7 |
| 116 | `infra-ci-ops-G13` | **major** | infra-ci-ops | Dev sizing is the documented PHI pilot target but is not HIPAA-durable: single-AZ, 1-day backups, no deletion protection, 30-day artifact auto-delete | confirmed | 0.25 day |  |
| 117 | `infra-ci-ops-G6` | **major** | infra-ci-ops | VPC flow logs will not deliver: flow-log IAM role has no permissions policy | confirmed | 0.25 day |  |
| 118 | `infra-ci-ops-G7` | **major** | infra-ci-ops | No monitoring/alerting: zero CloudWatch alarms, no SNS, despite RUNBOOK/README/deployment.md claims | confirmed | 1 day |  |
| 119 | `infra-ci-ops-G8` | **major** | infra-ci-ops | HIPAA technical controls missing: CloudTrail, AWS Config, Security Hub standards, encrypted log groups, VPC endpoints, WAF, ALB access logs, S3 TLS-only policy, RDS force_ssl, AWS Backup, dev GuardDuty | adjusted | 2-3 days |  |
| 120 | `infra-ci-ops-G9` | **major** | infra-ci-ops | ios-ci is a silent no-op (wrong workspace path, failure swallowed) | confirmed | 0.5 day |  |
| 121 | `ios-app-G10` | **major** | ios-app | PHI persists on disk via WKWebView default data store and is never cleared | confirmed | 0.5 day |  |
| 122 | `ios-app-G11` | **major** | ios-app | Mesh viewer depends on engine's process-local cache (404 after restart) | confirmed | 1 day (engine) | engine-api-auth-storage-G2 |
| 123 | `ios-app-G13` | **major** | ios-app | Burst capture can hang forever and holds ~60 full-resolution frames in memory | adjusted | 0.5-1 day |  |
| 124 | `ios-app-G14` | **major** | ios-app | API base URL override is dead config; production URL hardcoded | confirmed | 1 hour |  |
| 125 | `ios-app-G4` | **major** | ios-app | No session persistence, no Keychain, no on-device idle timeout or 401 handling | confirmed | 1-2 days |  |
| 126 | `ios-app-G5` | **major** | ios-app | 'Offline queue' does not exist: UploadService is in-memory and unused | adjusted | 2-3 days |  |
| 127 | `ios-app-G6` | **major** | ios-app | Fiducial detection is unwired and is not ArUco | adjusted | 2-4 days |  |
| 128 | `ios-app-G7` | **major** | ios-app | Probe entry and boundary annotation are placeholders with hardcoded values | confirmed | 3-5 days |  |
| 129 | `ios-app-G8` | **major** | ios-app | Depth/RGB artifacts are not in an engine-consumable format; RGB never captured | adjusted | 1-2 days iOS + engine decoder |  |
| 130 | `ios-app-G9` | **major** | ios-app | iOS CI cannot fail and never runs tests | confirmed | 1-2 hours | infra-ci-ops-G9 |
| 131 | `web-marketing-G2` | **major** | web-marketing | '95% CI on every measurement / depth, perimeter, footprint' overstates engine output | confirmed | 1 hour copy, or 1-2 days engine |  |
| 132 | `web-marketing-G3` | **major** | web-marketing | Architecture diagram and 'SAM' segmentation describe systems not in this repo | confirmed | half a day | contract-regulatory-F7 |
| 133 | `web-marketing-G4` | **major** | web-marketing | Portal tour presents mock-only features as working software (48-h rule, HCPCS/LCD scoring, route optimisation, expiry/waste alerts, peri-wound area, length/width, top-view/cross-section diagrams) | adjusted | copy: 2 hours; engine features: 1-2 weeks |  |
| 134 | `web-marketing-G5` | **major** | web-marketing | Deployed 'Portal sign in' CTA grants a clinician session to any credentials when no engine is reachable | adjusted | 1 hour | web-portal-G7 |
| 135 | `web-portal-G10` | **major** | web-portal | MeshWorkspace fabricates length/width/tissue and ships inert controls; 'tissue' mode is depth banding | confirmed | 0.5-1 day |  |
| 136 | `web-portal-G14` | **major** | web-portal | Global Permissions-Policy kills the live camera preview but not the handoff; no CSP | confirmed | 1 hour |  |
| 137 | `web-portal-G2` | **major** | web-portal | Mesh viewer Z-sign convention is inverted relative to the engine; only the bundled demo OBJ renders correctly | adjusted | 3-4 hours incl. verification against an engine-produced OBJ |  |
| 138 | `web-portal-G3` | **major** | web-portal | Progression ordering assumption (latest-first) breaks 'latest', 'prior', depth series and chart order against real engine data | adjusted | 1-2 hours |  |
| 139 | `web-portal-G4` | **major** | web-portal | Capture-handoff API is fully unauthenticated and serves uploaded patient photos + labels by URL id | adjusted | 1 day including storage swap |  |
| 140 | `web-portal-G5` | **major** | web-portal | NotesPanel reimbursement checkbox is inert server-side, demo measurement ids are not UUIDs, patient token is a literal | adjusted | 3-4 hours |  |
| 141 | `web-portal-G6` | **major** | web-portal | Proxy 3s abort spans body streaming and swaps in the demo mesh on any engine error, with no visible indicator | confirmed | 3-4 hours |  |
| 142 | `web-portal-G8` | **major** | web-portal | Admin pages are stubs on a legacy Header with dead links, although the engine already exposes the data | confirmed | 1 day | contract-web-engine-F7 |
| 143 | `web-portal-G9` | **major** | web-portal | Shell hardcodes identity, uptime, and compliance certifications; Topbar search/filters are decorative | confirmed | 0.5 day | contract-web-engine-F7 |
| 144 | `contract-env-secrets-F10` | **minor** | contract-env-secrets | Old-brand identifiers (albacetemeddev.com, com.albacetemeddev.woundscan, team RWG4WRX8A8, 'WoundScan') remain baked into iOS, terraform, App Store tooling and parts of the web | adjusted |  | infra-ci-ops-G16 |
| 145 | `contract-env-secrets-F11` | **minor** | contract-env-secrets | CORS, bind address/port and readiness are hardcoded and not environment-driven | adjusted |  | contract-security-phi-F9 |
| 146 | `contract-env-secrets-F12` | **minor** | contract-env-secrets | docker-compose bakes dev secrets and exposes Postgres/Redis on host ports with no override mechanism | confirmed |  | engine-tests-docs-packaging-G8 |
| 147 | `contract-ios-engine-F10` | **minor** | contract-ios-engine | App presents 'Recent captures' but the engine has no measurement-list endpoint | confirmed |  |  |
| 148 | `contract-ios-engine-F9` | **minor** | contract-ios-engine | UploadService is not the durable offline queue its header claims; jobs are dropped silently and in-flight slots are held during backoff | confirmed |  | ios-app-G5 |
| 149 | `contract-security-phi-F19` | **minor** | contract-security-phi | iOS: token never persisted (Keychain stub), raw JWT seeded into a non-secure WKWebView cookie, unused Photos permission, no offline queue | confirmed |  | ios-app-G4 |
| 150 | `contract-security-phi-F20` | **minor** | contract-security-phi | CI security scans are non-blocking (bandit/pip-audit '\|\| true', npm install --no-audit) | confirmed |  | infra-ci-ops-G10 |
| 151 | `contract-security-phi-F21` | **minor** | contract-security-phi | Weak defaults and dev credentials baked into code and compose | confirmed |  | engine-tests-docs-packaging-G8 |
| 152 | `contract-web-engine-F10` | **minor** | contract-web-engine | Notes reimbursement option is a no-op and demo ids are not UUIDs | adjusted |  | web-portal-G5 |
| 153 | `contract-web-engine-F11` | **minor** | contract-web-engine | Direct server-side engine fetches have no timeout | confirmed |  |  |
| 154 | `contract-web-engine-F5` | **minor** | contract-web-engine | Global Permissions-Policy camera=() disables getUserMedia on the mobile capture page | adjusted |  | web-portal-G14 |
| 155 | `contract-web-engine-F8` | **minor** | contract-web-engine | API client is dead, split across two env vars, and POST responses are not validated | adjusted |  | web-portal-G11 |
| 156 | `contract-web-engine-F9` | **minor** | contract-web-engine | Broken navigation targets: /phantom and /patients/{id} do not exist | confirmed |  | web-portal-G15 |
| 157 | `critic-G10` | **minor** | critic | No skip-to-content link and no automated accessibility check in CI for the portal (web-marketing-G10 covers marketing components only) | confirmed | 0.5 day |  |
| 158 | `critic-G13` | **minor** | critic | Vercel deployment is configured only in the dashboard (no vercel.json, no .env.example): env vars, domains, region and preview-deployment protection are unversioned, and every preview deployment carries the demo login | adjusted | 0.5 day |  |
| 159 | `critic-G14` | **minor** | critic | Public /demo renders a 'Download PDF' control that returns 401 (measurementId='demo' through the authenticated proxy) | adjusted | 1 hour |  |
| 160 | `critic-G15` | **minor** | critic | PartnershipSection asserts partner-tier, funding-review and 'the POC architecture carries production' claims that nothing in the repository substantiates | adjusted | 1 hour copy review |  |
| 161 | `critic-G17` | **minor** | critic | No transactional email capability and no DNS/email-authentication records in IaC; all contact paths are mailto links to a personal mailbox | adjusted | 1 day |  |
| 162 | `critic-G7` | **minor** | critic | No privacy manifest (PrivacyInfo.xcprivacy) and no App Privacy declaration tracked for a medical-category app that captures photos and depth data | confirmed | 0.5 day |  |
| 163 | `critic-G8` | **minor** | critic | No repository governance: no CODEOWNERS, dependabot/renovate, PR template, SECURITY.md or CONTRIBUTING; web CI installs with npm install so the lockfile is not enforced | adjusted | 0.5 day |  |
| 164 | `engine-api-auth-storage-G14` | **minor** | engine-api-auth-storage | Readiness probe, metrics and docs are unguarded or misleading | confirmed | 0.5 day | contract-security-phi-F9 |
| 165 | `engine-api-auth-storage-G15` | **minor** | engine-api-auth-storage | CORS wildcard | confirmed | 0.25 day | contract-security-phi-F9 |
| 166 | `engine-api-auth-storage-G16` | **minor** | engine-api-auth-storage | No global exception handling or request-id; enum ValueErrors become 500s | confirmed | 0.5 day | contract-security-phi-F9 |
| 167 | `engine-api-auth-storage-G17` | **minor** | engine-api-auth-storage | /admin/ml-metrics is a stub and product/user management endpoints are absent | adjusted | 2-3 days |  |
| 168 | `engine-api-auth-storage-G18` | **minor** | engine-api-auth-storage | Provenance and quality inputs are hardcoded placeholders | confirmed | 1 day (after G3) | engine-output-business-G7 |
| 169 | `engine-api-auth-storage-G19` | **minor** | engine-api-auth-storage | Notes: no amendment flow, misused audit actions, schema drift | confirmed | 1 day | engine-output-business-G9 |
| 170 | `engine-api-auth-storage-G20` | **minor** | engine-api-auth-storage | Grafts: HCPCS/CPT not derived from catalogue; inventory is a proxy; audit action misused | adjusted | 1-2 days |  |
| 171 | `engine-api-auth-storage-G21` | **minor** | engine-api-auth-storage | Test suite cannot catch the above because it only exercises the dev backdoor and in-memory paths | adjusted | 2-3 days | engine-tests-docs-packaging-G2 |
| 172 | `engine-api-auth-storage-G9` | **minor** | engine-api-auth-storage | Celery worker is deployed but unreachable: nothing enqueues, no job-status API | adjusted | 2-3 days |  |
| 173 | `engine-core-math-G10` | **minor** | engine-core-math | Monte Carlo correlated-noise sampler is loosely tied to the GP posterior | confirmed | 4-8 h |  |
| 174 | `engine-core-math-G11` | **minor** | engine-core-math | Synthesis determinism depends on the optional `noise` package; degradation config has dead fields; multiframe docstring overstates registration | confirmed | 2-4 h |  |
| 175 | `engine-core-math-G12` | **minor** | engine-core-math | Small correctness/API polish items in geometry | adjusted | 1-2 h |  |
| 176 | `engine-core-math-G8` | **minor** | engine-core-math | GPyTorch/GPy sparse backend is claimed but absent; unused optional extra | confirmed | 1-2 h | engine-tests-docs-packaging-G11 |
| 177 | `engine-core-math-G9` | **minor** | engine-core-math | np.trapz is deprecated on numpy 2.x; lockfile and dev venv disagree on numpy major version | confirmed | 1 h |  |
| 178 | `engine-ml-quality-validation-G10` | **minor** | engine-ml-quality-validation | All quality/validation thresholds are assumed constants with no data derivation and internal doc/code mismatches | confirmed | 2-3 days engineering + validation study time |  |
| 179 | `engine-ml-quality-validation-G11` | **minor** | engine-ml-quality-validation | Phantom calibration: no data, duplicate logic, in-memory storage, ORM table never written | confirmed | 1 day (code); phantom procurement external |  |
| 180 | `engine-ml-quality-validation-G12` | **minor** | engine-ml-quality-validation | Model registry never populated; empty-hash cards possible | confirmed | 0.5 day | engine-output-business-G7 |
| 181 | `engine-ml-quality-validation-G13` | **minor** | engine-ml-quality-validation | U-Net inference path is not production-safe | adjusted | 0.5-1 day |  |
| 182 | `engine-ml-quality-validation-G14` | **minor** | engine-ml-quality-validation | Plausibility box-bound check passes any volume when max_depth is 0 | confirmed | 15 min |  |
| 183 | `engine-ml-quality-validation-G15` | **minor** | engine-ml-quality-validation | Docs, admin endpoint and marketing overstate ML/monitoring capability | adjusted | 0.5 day | engine-tests-docs-packaging-G6 |
| 184 | `engine-ml-quality-validation-G16` | **minor** | engine-ml-quality-validation | RobustFiducialDetector: unused field, missing promised fallback, not used by pipeline | confirmed | 1-2 days |  |
| 185 | `engine-ml-quality-validation-G9` | **minor** | engine-ml-quality-validation | Motion-artifact thresholds have a units bug (mm vs mm/s) that saturates any real burst | adjusted | 0.5 day |  |
| 186 | `engine-output-business-G11` | **minor** | engine-output-business | POST /notes returns 500 when a prior area/volume of 0.0 is supplied | confirmed | 1 hour |  |
| 187 | `engine-output-business-G12` | **minor** | engine-output-business | CSV export and trajectory plot are dead code; EXPORT_CSV audit action never used | adjusted | 0.5-1 day |  |
| 188 | `engine-output-business-G13` | **minor** | engine-output-business | reportlab markup injection via unescaped product names, rationale and provenance text | adjusted | 1 hour |  |
| 189 | `engine-output-business-G15` | **minor** | engine-output-business | Integration test for /notes posts non-existent field names, so the real subjective fields are untested | confirmed | 1 hour |  |
| 190 | `engine-output-business-G16` | **minor** | engine-output-business | Reimbursement embedded in notes uses max package size across multiple grafts | confirmed | 1 hour |  |
| 191 | `engine-tests-docs-packaging-G10` | **minor** | engine-tests-docs-packaging | No conftest; integration fixtures mutate os.environ globally without teardown | confirmed | 1-2 hours |  |
| 192 | `engine-tests-docs-packaging-G11` | **minor** | engine-tests-docs-packaging | Dead 'gp' extra and environment-dependent 'Perlin' noise backend | confirmed | 1-2 hours |  |
| 193 | `engine-tests-docs-packaging-G12` | **minor** | engine-tests-docs-packaging | Tests are excluded from lint/format enforcement | adjusted | 1 hour |  |
| 194 | `engine-tests-docs-packaging-G13` | **minor** | engine-tests-docs-packaging | Utility scripts are misdocumented or non-portable | confirmed | 1 hour |  |
| 195 | `engine-tests-docs-packaging-G15` | **minor** | engine-tests-docs-packaging | Postgres version drift between compose, docs and tests | confirmed | 10 minutes |  |
| 196 | `engine-tests-docs-packaging-G9` | **minor** | engine-tests-docs-packaging | CI never executes the torch or testcontainers tests (the 5 skips) | adjusted | 0.5-1 day |  |
| 197 | `infra-ci-ops-G11` | **minor** | infra-ci-ops | DNS/ACM is manual and hostnames disagree across docs | adjusted | 0.5 day |  |
| 198 | `infra-ci-ops-G14` | **minor** | infra-ci-ops | Terraform hygiene: no variables/tfvars, lock file gitignored, no default_tags, no fmt/validate, README wrong on layout | confirmed | 0.5 day |  |
| 199 | `infra-ci-ops-G15` | **minor** | infra-ci-ops | bin/ scripts are laptop-bound: screenshots need gitignored PNGs + macOS font, asc embeds a personal path, ship-ios --auto key path mismatch | adjusted | 0.25 day | ios-app-G18 |
| 200 | `infra-ci-ops-G16` | **minor** | infra-ci-ops | App Store metadata stale: no privacy policy URL, WoundScan/albacetemeddev branding vs StrataMetric AI rebrand, screenshot sizes | confirmed | 0.25 day |  |
| 201 | `infra-ci-ops-G17` | **minor** | infra-ci-ops | Health checks are static; readiness does not verify DB/S3 | adjusted | 0.25 day | contract-security-phi-F9 |
| 202 | `infra-ci-ops-G18` | **minor** | infra-ci-ops | regulatory.yml only on PRs; traceability check is shallow; web-ci PR filter misses its own file | adjusted | 0.25 day |  |
| 203 | `infra-ci-ops-G5` | **minor** | infra-ci-ops | No Redis/ElastiCache and no Celery worker service anywhere, despite docs; prod does not set WS_CELERY_EAGER | adjusted | 0.25 day for (a); 1-2 days for (b) | engine-api-auth-storage-G9 |
| 204 | `ios-app-G12` | **minor** | ios-app | Warmup readiness is fake; double ARSession start; no LiDAR runtime gate or user message | adjusted | 0.5 day |  |
| 205 | `ios-app-G16` | **minor** | ios-app | Dead code and doc drift (unused models/services, static HistoryView, hardcoded version, unused permission strings) | confirmed | 0.5 day |  |
| 206 | `ios-app-G17` | **minor** | ios-app | bin/ship-ios --auto validates ASC_API_KEY_PATH but never gives it to altool | adjusted | 30 minutes | ios-app-G18 |
| 207 | `ios-app-G18` | **minor** | ios-app | App Store screenshot pipeline depends on absent, gitignored inputs and shows the web portal instead of the app | adjusted | 0.5-1 day |  |
| 208 | `ios-app-G19` | **minor** | ios-app | Test coverage limited to three Codable checks | confirmed | 1-2 days |  |
| 209 | `web-marketing-G10` | **minor** | web-marketing | Accessibility and reduced-motion gaps | confirmed | half a day |  |
| 210 | `web-marketing-G11` | **minor** | web-marketing | robots.txt disallow list misses several portal paths | confirmed | 5 minutes |  |
| 211 | `web-marketing-G12` | **minor** | web-marketing | OG card pipeline is manual and uses different fonts from the site | confirmed | 2-3 hours |  |
| 212 | `web-marketing-G13` | **minor** | web-marketing | No CSP header despite 'hardened security headers' claim | confirmed | half a day | web-portal-G14 |
| 213 | `web-marketing-G6` | **minor** | web-marketing | ~1 MB PNG favicons/apple icon and JSON-LD logo | adjusted | 1-2 hours |  |
| 214 | `web-marketing-G7` | **minor** | web-marketing | Homepage is fully dynamic (uncached) because of getSession() | adjusted | 1 hour |  |
| 215 | `web-marketing-G8` | **minor** | web-marketing | Partnership section missing from nav; nav hidden below 1280px | confirmed | 15 minutes |  |
| 216 | `web-marketing-G9` | **minor** | web-marketing | Stale/inconsistent copy and demo numbers | adjusted | 1-2 hours |  |
| 217 | `web-portal-G11` | **minor** | web-portal | Unused dependencies and dead client code; EOL/lagging majors | confirmed | 1-2 hours to prune; 1-2 days for the upgrade |  |
| 218 | `web-portal-G12` | **minor** | web-portal | Date-only strings formatted in local TZ shift by one day and cause SSR/CSR hydration mismatches | confirmed | 1 hour |  |
| 219 | `web-portal-G13` | **minor** | web-portal | Realistic PHI-shaped fixtures and real-looking practice identifiers are hardcoded and shipped in the bundle; sample data sits on the real-data path | confirmed | 2 hours |  |
| 220 | `web-portal-G15` | **minor** | web-portal | Wound list and boards link into non-existent or hardcoded targets | confirmed | 2-3 hours |  |
| 221 | `contract-env-secrets-F14` | **info** | contract-env-secrets | OTLP tracing depends on implicit OTEL_* env but the exporter package is not installed, so tracing is silently disabled everywhere | adjusted |  | engine-ml-quality-validation-G7 |
| 222 | `contract-env-secrets-F15` | **info** | contract-env-secrets | No secrets or .env files are tracked in git; .env handling is consistent | confirmed |  |  |
| 223 | `contract-ios-engine-F11` | **info** | contract-ios-engine | ProbeRecord serialises an extra 'id' key; tolerated only because engine models use pydantic's default extra='ignore' | confirmed |  |  |
| 224 | `contract-ios-engine-F12` | **info** | contract-ios-engine | No cross-repo contract tests: iOS tests never decode engine JSON, engine tests only run with the dev-login flag | confirmed |  | contract-web-engine-F13 |
| 225 | `contract-security-phi-F22` | **info** | contract-security-phi | Controls verified as correctly implemented | confirmed |  |  |
| 226 | `contract-web-engine-F12` | **info** | contract-web-engine | Logout does not revoke the engine session; engine JWT check ignores its session store | adjusted |  | engine-api-auth-storage-G6 |
| 227 | `contract-web-engine-F13` | **info** | contract-web-engine | No web tests and no contract tests between zod schemas and pydantic models | confirmed |  |  |
| 228 | `critic-G11` | **info** | critic | Dependency licensing is clean (no GPL/AGPL); engine declares Proprietary; LGPL only via psycopg2-binary and sharp's bundled libvips; no third-party notices generated | adjusted | 0.25 day |  |
| 229 | `critic-G12` | **info** | critic | Git history contains no secrets, keys, tokens or .env files (verified across all 118 commits) | adjusted | 0 |  |
| 230 | `critic-G5` | **info** | critic | No analytics, telemetry or cookie-consent mechanism exists (functional cookie and theme localStorage only) | confirmed | 0 |  |
| 231 | `critic-G9` | **info** | critic | English-only: no i18n framework on web, en-US formatters hardcoded, no iOS localization files | confirmed | 0 |  |
| 232 | `engine-output-business-G14` | **info** | engine-output-business | OBJ mesh is an open height-field, not the 'closed surface' the docstring promises; pure-Python loops | adjusted | 0.5 day |  |
