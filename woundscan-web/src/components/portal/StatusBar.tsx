export function StatusBar({
  auditCount,
  systemStatus = 99.99,
  compliance = 98,
}: {
  auditCount: number;
  systemStatus?: number;
  compliance?: number;
}) {
  return (
    <div className="sticky bottom-0 z-10 border-t border-hairline bg-surface/90 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-2 text-[11px]">
        <div className="flex items-center gap-2 text-ink-soft">
          <span className="grid h-4 w-4 place-items-center rounded-full bg-success/20 text-success">
            <ShieldIcon />
          </span>
          <span>
            Enterprise-grade security &amp; compliance
            <span className="mx-2 text-ink-muted/50">·</span>
            HIPAA · SOC 2 Type II · 256-bit AES
          </span>
        </div>
        <div className="flex items-center gap-4 text-ink-muted">
          <span>
            <span className="text-ink-soft">{auditCount.toLocaleString()}</span> audit events
          </span>
          <span>
            System uptime <span className="text-success">{systemStatus.toFixed(2)}%</span>
          </span>
          <span>
            Compliance <span className="text-accent">{compliance}%</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function ShieldIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}
