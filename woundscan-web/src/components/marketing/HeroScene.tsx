"use client";

import { Suspense, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { Grid, Html, OrbitControls } from "@react-three/drei";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import * as THREE from "three";

/**
 * Hero visual: the real synthetic wound mesh from the measurement engine,
 * depth-shaded, slowly rotating, with a LiDAR-style scan ring sweeping
 * across it and live measurement callouts. Interactive — drag to orbit.
 */
export function HeroScene() {
  const [ready, setReady] = useState(false);
  return (
    <div
      className="relative h-full w-full overflow-hidden rounded-2xl"
      style={{ background: "radial-gradient(ellipse at 50% 40%, #0a1428 0%, #03060d 75%)" }}
    >
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0.1, 1.35, 2.6], fov: 42, near: 0.05, far: 40 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={() => setReady(true)}
      >
        <color attach="background" args={["#03060d"]} />
        <fog attach="fog" args={["#03060d", 5.5, 12]} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[3, 4, 2]} intensity={1.1} />
        <directionalLight position={[-3, 2, -2]} intensity={0.5} color="#7dd3fc" />

        <Suspense fallback={null}>
          <SpinGroup>
            <WoundSurface />
            <ScanRing />
          </SpinGroup>
        </Suspense>

        <Grid
          position={[0, -0.5, 0]}
          args={[14, 14]}
          cellSize={0.25}
          cellThickness={0.5}
          cellColor="#0e3a5e"
          sectionSize={1}
          sectionThickness={0.9}
          sectionColor="#155e75"
          fadeDistance={8}
          fadeStrength={1.6}
          infiniteGrid
        />

        <OrbitControls
          enablePan={false}
          enableZoom={false}
          minPolarAngle={Math.PI / 4.2}
          maxPolarAngle={Math.PI / 2.05}
          target={[0, -0.05, 0]}
        />
      </Canvas>

      {/* HUD chrome (DOM, sits above the canvas) */}
      <div className="pointer-events-none absolute inset-0">
        <span className="mk-scanline" style={{ animationDelay: "1.2s" }} />
        {/* Corner brackets */}
        <Corner className="left-3 top-3 rotate-0" />
        <Corner className="right-3 top-3 rotate-90" />
        <Corner className="bottom-3 right-3 rotate-180" />
        <Corner className="bottom-3 left-3 -rotate-90" />

        <div className="absolute left-4 top-4 flex flex-col gap-1 font-mono text-[10px] leading-relaxed text-cyan-200/70">
          <span>LIDAR·BURST 60f/4.0s</span>
          <span>FUSION heteroscedastic-GP</span>
          <span>SEGMENT sam-vit-h</span>
        </div>
        <div className="absolute bottom-4 left-4 flex items-center gap-2 font-mono text-[10px] text-cyan-200/70">
          <span className="mk-live-dot inline-block h-1.5 w-1.5 rounded-full bg-success" />
          <span>{ready ? "MESH RECONSTRUCTED · drag to orbit" : "RECONSTRUCTING…"}</span>
        </div>
        <div className="absolute bottom-4 right-4 rounded border border-cyan-300/20 bg-cyan-300/5 px-2 py-1 font-mono text-[10px] text-cyan-100/80">
          uncertainty ±0.3 mm @95%
        </div>
      </div>
    </div>
  );
}

function Corner({ className }: { className: string }) {
  return (
    <svg
      className={`absolute h-5 w-5 text-cyan-300/40 ${className}`}
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden
    >
      <path d="M1 7V1h6" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function SpinGroup({ children }: { children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null!);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.18;
  });
  return <group ref={ref}>{children}</group>;
}

/** Loads the engine's demo OBJ, normalizes it, and depth-shades it. */
function WoundSurface() {
  const obj = useLoader(OBJLoader, "/demo-wound.obj");

  const { geometry, labels } = useMemo(() => {
    let source: THREE.BufferGeometry | null = null;
    obj.traverse((c) => {
      if (!source && (c as THREE.Mesh).isMesh) {
        source = ((c as THREE.Mesh).geometry as THREE.BufferGeometry).clone();
      }
    });
    const g = source ?? new THREE.BufferGeometry();
    g.computeBoundingBox();
    const bb = g.boundingBox ?? new THREE.Box3();
    const center = bb.getCenter(new THREE.Vector3());
    const size = bb.getSize(new THREE.Vector3());
    const longest = Math.max(size.x, size.y, size.z) || 1;
    const scale = 1.9 / longest;
    g.translate(-center.x, -center.y, -center.z);
    g.scale(scale, scale, scale);
    // Engine frame: bed in XY, +Z below skin → rotate so depth runs -Y.
    g.rotateX(-Math.PI / 2);
    g.computeVertexNormals();
    g.computeBoundingBox();
    const nb = g.boundingBox ?? new THREE.Box3();
    const min = nb.min.y;
    const range = nb.max.y - nb.min.y || 1;

    // Depth-shaded vertex colors: rim skin-blue → deep indigo core.
    const pos = g.getAttribute("position") as THREE.BufferAttribute;
    const colors = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
      const t = (pos.getY(i) - min) / range; // 0 deepest → 1 rim
      colors[i * 3] = 0.05 + 0.08 * t;
      colors[i * 3 + 1] = 0.28 + 0.5 * t;
      colors[i * 3 + 2] = 0.5 + 0.42 * t;
    }
    g.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    return {
      geometry: g,
      labels: {
        // Measurement callout anchor points on the normalized mesh.
        length: [0, -nb.min.y * 0.1 + 0.06, nb.max.z + 0.12] as [number, number, number],
        depth: [nb.min.x - 0.28, nb.min.y + 0.1, 0] as [number, number, number],
        area: [nb.max.x + 0.24, 0.14, -0.1] as [number, number, number],
      },
    };
  }, [obj]);

  return (
    <group>
      <mesh geometry={geometry}>
        <meshStandardMaterial vertexColors roughness={0.45} metalness={0.1} side={THREE.DoubleSide} />
      </mesh>
      <mesh geometry={geometry}>
        <meshBasicMaterial color="#22d3ee" wireframe transparent opacity={0.08} />
      </mesh>
      <Callout position={labels.length} text="L 42.0 mm" />
      <Callout position={labels.depth} text="D 11.8 mm" />
      <Callout position={labels.area} text="Bed 11.2 cm²" />
    </group>
  );
}

function Callout({ position, text }: { position: [number, number, number]; text: string }) {
  return (
    <Html position={position} center distanceFactor={3.4} style={{ pointerEvents: "none" }}>
      <span className="whitespace-nowrap rounded border border-cyan-300/30 bg-[#03060d]/80 px-1.5 py-0.5 font-mono text-[10px] text-cyan-100 shadow-[0_0_14px_rgba(34,211,238,0.25)]">
        {text}
      </span>
    </Html>
  );
}

/** Expanding LiDAR-style scan ring that sweeps the surface. */
function ScanRing() {
  const ref = useRef<THREE.Mesh>(null!);
  const mat = useRef<THREE.MeshBasicMaterial>(null!);
  useFrame(({ clock }) => {
    const t = (clock.elapsedTime % 3.2) / 3.2;
    const r = 0.05 + t * 1.35;
    if (ref.current) ref.current.scale.setScalar(r);
    if (mat.current) mat.current.opacity = 0.55 * (1 - t);
  });
  return (
    <mesh ref={ref} position={[0, 0.02, 0]} rotation-x={-Math.PI / 2}>
      <ringGeometry args={[0.96, 1, 96]} />
      <meshBasicMaterial ref={mat} color="#22d3ee" transparent opacity={0.5} side={THREE.DoubleSide} />
    </mesh>
  );
}
