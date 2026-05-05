"use client";

/**
 * Mesh canvas placeholder. Once the GLTF viewer is wired up (three.js +
 * @react-three/fiber), this component will host the WebGL surface; for
 * now it renders a styled stand-in so the layout, controls, and theming
 * can be reviewed end-to-end.
 *
 * Behavior:
 *  - Always rendered against a dark canvas regardless of theme — 3D
 *    surfaces read better on near-black, and it matches the mockup.
 *  - Shows a teal halo + radial grid; mode toggles tweak the visual
 *    treatment so render-mode/layer toggles feel live.
 */
type Layers = {
  mesh: boolean;
  depthMap: boolean;
  heatMap: boolean;
  tissueLayers: boolean;
  measurements: boolean;
};

type Props = {
  meshUrl: string | null;
  mode: "realistic" | "wireframe" | "tissue";
  layers: Layers;
  analytics: boolean;
};

export function MeshCanvas({ meshUrl, mode, layers, analytics }: Props) {
  return (
    <div
      className="relative h-[640px] w-full overflow-hidden"
      style={{ background: "radial-gradient(ellipse at center, #0a1428 0%, #03060d 70%)" }}
    >
      {/* Background grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            "linear-gradient(rgba(34,211,238,0.10) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.10) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          maskImage: "radial-gradient(ellipse at center, black 50%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 50%, transparent 80%)",
        }}
      />

      {/* Halo */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[420px] w-[620px] -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          background:
            "radial-gradient(closest-side, rgba(34,211,238,0.30), rgba(34,211,238,0.05) 60%, transparent 75%)",
          filter: "blur(2px)",
        }}
      />

      {/* "mesh" placeholder shape */}
      {layers.mesh && (
        <svg
          viewBox="0 0 600 360"
          className="absolute left-1/2 top-1/2 h-[360px] w-[600px] -translate-x-1/2 -translate-y-1/2"
          aria-hidden="true"
        >
          <defs>
            <radialGradient id="wound-fill" cx="50%" cy="45%" r="60%">
              <stop offset="0%" stopColor="#7a1d1d" />
              <stop offset="55%" stopColor="#b34141" />
              <stop offset="80%" stopColor="#3a2a2a" />
              <stop offset="100%" stopColor="#1a1010" />
            </radialGradient>
            <radialGradient id="wound-rim" cx="50%" cy="50%" r="55%">
              <stop offset="60%" stopColor="transparent" />
              <stop offset="78%" stopColor="rgba(255,200,180,0.35)" />
              <stop offset="100%" stopColor="transparent" />
            </radialGradient>
            <pattern id="wire" width="14" height="14" patternUnits="userSpaceOnUse">
              <path d="M0 7 L14 7 M7 0 L7 14" stroke="rgba(34,211,238,0.55)" strokeWidth="0.5" />
            </pattern>
          </defs>

          <ellipse cx="300" cy="180" rx="240" ry="120" fill="url(#wound-fill)" opacity="0.95" />
          <ellipse cx="300" cy="180" rx="240" ry="120" fill="url(#wound-rim)" />

          {mode === "wireframe" && (
            <ellipse
              cx="300"
              cy="180"
              rx="240"
              ry="120"
              fill="url(#wire)"
              opacity="0.6"
            />
          )}
          {mode === "tissue" && (
            <>
              <ellipse cx="300" cy="180" rx="220" ry="105" fill="rgba(245,158,11,0.18)" />
              <ellipse cx="270" cy="170" rx="120" ry="55" fill="rgba(239,68,68,0.22)" />
              <ellipse cx="340" cy="195" rx="60" ry="32" fill="rgba(120,113,108,0.30)" />
            </>
          )}

          {layers.measurements && (
            <g stroke="rgba(34,211,238,0.85)" strokeWidth="1" fill="none">
              <line x1="60" y1="180" x2="540" y2="180" />
              <line x1="300" y1="60" x2="300" y2="300" />
              <text x="555" y="184" fontSize="11" fill="rgb(125,211,252)">L</text>
              <text x="296" y="56" fontSize="11" fill="rgb(125,211,252)">W</text>
            </g>
          )}

          {layers.heatMap && (
            <ellipse
              cx="300"
              cy="180"
              rx="240"
              ry="120"
              fill="url(#wound-fill)"
              opacity="0.0"
              style={{ mixBlendMode: "screen" }}
            />
          )}
        </svg>
      )}

      {/* Bottom turquoise glow disk */}
      <div
        className="pointer-events-none absolute left-1/2 top-[68%] h-[80px] w-[640px] -translate-x-1/2 rounded-full"
        style={{
          background:
            "radial-gradient(closest-side, rgba(34,211,238,0.55), transparent 75%)",
          filter: "blur(8px)",
        }}
      />

      {/* HUD chips */}
      <div className="absolute left-4 top-20 z-10 flex flex-col gap-1 text-[11px] text-cyan-200/80">
        <span>· orient: free</span>
        <span>· lighting: studio</span>
        <span>
          · mode:{" "}
          <span className="capitalize text-cyan-100">{mode}</span>
        </span>
        {analytics && <span className="text-amber-200/90">· analytics overlay</span>}
        {!meshUrl && (
          <span className="mt-2 rounded border border-cyan-300/20 bg-cyan-300/5 px-2 py-1 text-cyan-100/80">
            Awaiting mesh upload
          </span>
        )}
      </div>
    </div>
  );
}
