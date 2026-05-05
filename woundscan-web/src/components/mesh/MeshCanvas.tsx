"use client";

import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import {
  Bounds,
  Environment,
  Grid,
  Html,
  OrbitControls,
  useBounds,
} from "@react-three/drei";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import * as THREE from "three";

type Layers = {
  mesh: boolean;
  depthMap: boolean;
  heatMap: boolean;
  tissueLayers: boolean;
  measurements: boolean;
};

type RenderMode = "realistic" | "wireframe" | "tissue";

type Props = {
  meshUrl: string | null;
  mode: RenderMode;
  layers: Layers;
  analytics: boolean;
  /** When true, OrbitControls performs slow continuous rotation. */
  autoRotate: boolean;
  /** Bumping this value asks the camera to refit to the mesh. */
  fitVersion: number;
  /** When true, a horizontal clip plane reveals a cross-section. */
  crossSection: boolean;
};

/**
 * WebGL wound-mesh viewer. The engine emits Wavefront OBJ in
 * millimeters, +Z below skin. We center / rescale the geometry,
 * recompute vertex normals, and color it by depth or anatomy
 * depending on the render mode.
 */
export function MeshCanvas({
  meshUrl,
  mode,
  layers,
  analytics,
  autoRotate,
  fitVersion,
  crossSection,
}: Props) {
  return (
    <div
      className="relative h-[640px] w-full overflow-hidden"
      style={{ background: "radial-gradient(ellipse at center, #0a1428 0%, #03060d 70%)" }}
    >
      <Canvas
        shadows
        dpr={[1, 2]}
        camera={{ position: [0, 1.2, 3.4], fov: 38, near: 0.05, far: 50 }}
        gl={{ antialias: true, localClippingEnabled: true }}
      >
        <color attach="background" args={["#03060d"]} />
        <fog attach="fog" args={["#03060d", 6, 14]} />

        <ambientLight intensity={0.45} />
        <directionalLight position={[3, 4, 2]} intensity={1.2} castShadow />
        <directionalLight position={[-3, 2, -2]} intensity={0.4} color="#7dd3fc" />

        <Suspense fallback={<LoaderBadge label="Loading mesh…" />}>
          {meshUrl ? (
            <Bounds fit clip observe margin={1.15}>
              <FitOnVersion version={fitVersion} />
              <WoundMesh
                url={meshUrl}
                mode={mode}
                visible={layers.mesh}
                heatMap={layers.heatMap}
                tissue={layers.tissueLayers}
                depthMap={layers.depthMap}
                showMeasurements={layers.measurements}
                crossSection={crossSection}
              />
            </Bounds>
          ) : (
            <PlaceholderMesh
              mode={mode}
              visible={layers.mesh}
              heatMap={layers.heatMap}
              tissue={layers.tissueLayers}
              showMeasurements={layers.measurements}
            />
          )}
        </Suspense>

        <Glow />
        <Grid
          position={[0, -0.42, 0]}
          args={[12, 12]}
          cellSize={0.25}
          cellThickness={0.6}
          cellColor="#0e3a5e"
          sectionSize={1}
          sectionThickness={1.0}
          sectionColor="#22d3ee"
          fadeDistance={9}
          fadeStrength={1.4}
          infiniteGrid
        />

        <Environment preset="studio" environmentIntensity={0.3} />
        <OrbitControls
          enablePan
          enableZoom
          autoRotate={autoRotate}
          autoRotateSpeed={0.7}
          minDistance={1.0}
          maxDistance={8}
          target={[0, 0, 0]}
        />
      </Canvas>

      {/* HUD overlay */}
      <div className="pointer-events-none absolute left-4 top-20 z-10 flex flex-col gap-1 text-[11px] text-cyan-200/80">
        <span>· orient: free</span>
        <span>· lighting: studio</span>
        <span>· mode: <span className="capitalize text-cyan-100">{mode}</span></span>
        {autoRotate && <span className="text-emerald-200/90">· auto-rotate</span>}
        {crossSection && <span className="text-amber-200/90">· cross-section on</span>}
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

function LoaderBadge({ label }: { label: string }) {
  return (
    <Html center>
      <span className="rounded border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs text-cyan-100">
        {label}
      </span>
    </Html>
  );
}

function FitOnVersion({ version }: { version: number }) {
  const bounds = useBounds();
  useEffect(() => {
    bounds.refresh().clip().fit();
  }, [version, bounds]);
  return null;
}

function Glow() {
  return (
    <mesh position={[0, -0.4, 0]} rotation-x={-Math.PI / 2}>
      <ringGeometry args={[0.45, 1.6, 64]} />
      <meshBasicMaterial color="#22d3ee" transparent opacity={0.18} />
    </mesh>
  );
}

/**
 * Loads a wound OBJ from the engine, normalises it to a unit-ish frame
 * (engine emits millimetres) and applies the chosen visualisation.
 */
function WoundMesh({
  url,
  mode,
  visible,
  heatMap,
  tissue,
  depthMap,
  showMeasurements,
  crossSection,
}: {
  url: string;
  mode: RenderMode;
  visible: boolean;
  heatMap: boolean;
  tissue: boolean;
  depthMap: boolean;
  showMeasurements: boolean;
  crossSection: boolean;
}) {
  const obj = useLoader(OBJLoader, url);
  const { invalidate } = useThree();

  // Normalize once: center, scale, recompute normals, color by depth.
  const { geometry, depthRange, bbox } = useMemo(() => {
    let merged: THREE.BufferGeometry | null = null;
    obj.traverse((c) => {
      if ((c as THREE.Mesh).isMesh) {
        const m = c as THREE.Mesh;
        const g = m.geometry as THREE.BufferGeometry;
        merged = merged ? mergeInto(merged, g.clone().applyMatrix4(m.matrixWorld)) : g.clone().applyMatrix4(m.matrixWorld);
      }
    });
    if (!merged) merged = new THREE.BufferGeometry();
    merged.computeBoundingBox();
    const bb = merged.boundingBox ?? new THREE.Box3();
    const center = bb.getCenter(new THREE.Vector3());
    const size = bb.getSize(new THREE.Vector3());
    const longest = Math.max(size.x, size.y, size.z) || 1;
    const scale = 1.6 / longest;
    merged.translate(-center.x, -center.y, -center.z);
    merged.scale(scale, scale, scale);
    merged.computeVertexNormals();
    merged.computeBoundingBox();
    const newBb = merged.boundingBox ?? new THREE.Box3();
    return {
      geometry: merged,
      depthRange: { min: newBb.min.z, max: newBb.max.z },
      bbox: { size: size.clone().multiplyScalar(scale), realSize: size },
    };
  }, [obj]);

  const clipPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, -1, 0), 0.05), []);

  // Colour palette per mode.
  const material = useMemo(() => {
    const base = (() => {
      if (mode === "wireframe") {
        return new THREE.MeshBasicMaterial({
          color: "#22d3ee",
          wireframe: true,
        });
      }
      if (mode === "tissue") {
        return new THREE.MeshStandardMaterial({
          vertexColors: true,
          roughness: 0.55,
          metalness: 0.05,
        });
      }
      return new THREE.MeshStandardMaterial({
        color: "#9b3838",
        roughness: 0.65,
        metalness: 0.05,
      });
    })();
    base.side = THREE.DoubleSide;
    if (crossSection) {
      base.clippingPlanes = [clipPlane];
      base.clipShadows = true;
    }
    return base;
  }, [mode, crossSection, clipPlane]);

  // Vertex colours for tissue / depth-map / heat-map modes.
  useEffect(() => {
    if (!geometry) return;
    const wantsVertexColor =
      mode === "tissue" || depthMap || heatMap || tissue;
    if (!wantsVertexColor) {
      geometry.deleteAttribute("color");
      invalidate();
      return;
    }
    const pos = geometry.getAttribute("position") as THREE.BufferAttribute;
    const n = pos.count;
    const colors = new Float32Array(n * 3);
    const range = depthRange.max - depthRange.min || 1;
    for (let i = 0; i < n; i++) {
      const z = pos.getZ(i);
      const t = (z - depthRange.min) / range; // 0 = deepest, 1 = shallowest
      let r = 0;
      let g = 0;
      let b = 0;
      if (heatMap) {
        // heat: blue → cyan → yellow → red as depth grows
        const d = 1 - t;
        const c = heatColor(d);
        r = c[0];
        g = c[1];
        b = c[2];
      } else if (depthMap) {
        // depth shaded sky → indigo
        r = 0.04 + 0.0 * t;
        g = 0.35 + 0.55 * t;
        b = 0.55 + 0.4 * t;
      } else {
        // tissue (granulation/slough/eschar) by depth bands
        if (t < 0.33) {
          r = 0.4;
          g = 0.32;
          b = 0.28;
        } else if (t < 0.66) {
          r = 0.85;
          g = 0.27;
          b = 0.27;
        } else {
          r = 0.95;
          g = 0.62;
          b = 0.18;
        }
      }
      colors[i * 3] = r;
      colors[i * 3 + 1] = g;
      colors[i * 3 + 2] = b;
    }
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    invalidate();
  }, [geometry, mode, depthMap, heatMap, tissue, depthRange, invalidate]);

  if (!visible || !geometry) return null;

  return (
    <group>
      <mesh geometry={geometry} material={material} castShadow receiveShadow />
      {showMeasurements && <BBoxAxes bbox={bbox} />}
    </group>
  );
}

function BBoxAxes({ bbox }: { bbox: { size: THREE.Vector3; realSize: THREE.Vector3 } }) {
  // realSize is in millimetres in the engine frame; size is the on-screen unit cube.
  const lx = bbox.size.x;
  const ly = bbox.size.y;
  const lz = bbox.size.z;
  const mmL = bbox.realSize.x.toFixed(0);
  const mmW = bbox.realSize.y.toFixed(0);
  const mmD = bbox.realSize.z.toFixed(0);
  return (
    <group>
      <Line from={[-lx / 2, -ly / 2, lz / 2]} to={[lx / 2, -ly / 2, lz / 2]} color="#22d3ee" />
      <Label position={[0, -ly / 2 - 0.08, lz / 2]} text={`L ${mmL} mm`} />
      <Line from={[-lx / 2, -ly / 2, lz / 2]} to={[-lx / 2, ly / 2, lz / 2]} color="#22d3ee" />
      <Label position={[-lx / 2 - 0.1, 0, lz / 2]} text={`W ${mmW} mm`} />
      <Line from={[-lx / 2, -ly / 2, lz / 2]} to={[-lx / 2, -ly / 2, -lz / 2]} color="#22d3ee" />
      <Label position={[-lx / 2 - 0.1, -ly / 2, 0]} text={`D ${mmD} mm`} />
    </group>
  );
}

function Line({
  from,
  to,
  color,
}: {
  from: [number, number, number];
  to: [number, number, number];
  color: string;
}) {
  const ref = useRef<THREE.BufferGeometry>(null!);
  useEffect(() => {
    if (!ref.current) return;
    ref.current.setFromPoints([new THREE.Vector3(...from), new THREE.Vector3(...to)]);
  }, [from, to]);
  return (
    <line>
      <bufferGeometry ref={ref} />
      <lineBasicMaterial color={color} />
    </line>
  );
}

function Label({ position, text }: { position: [number, number, number]; text: string }) {
  return (
    <Html position={position} center distanceFactor={4} style={{ pointerEvents: "none" }}>
      <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 font-mono text-[10px] text-cyan-100">
        {text}
      </span>
    </Html>
  );
}

/**
 * Stand-in shown when no measurement is available — a gently rotating
 * crater so the page still demos the layout end-to-end.
 */
function PlaceholderMesh({
  mode,
  visible,
  heatMap,
  tissue,
  showMeasurements,
}: {
  mode: RenderMode;
  visible: boolean;
  heatMap: boolean;
  tissue: boolean;
  showMeasurements: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.15;
  });
  const wireframe = mode === "wireframe";
  const color = wireframe ? "#22d3ee" : tissue || heatMap ? "#b34141" : "#9b3838";
  if (!visible) return null;
  return (
    <group>
      <mesh ref={ref} castShadow receiveShadow>
        <sphereGeometry args={[0.85, 64, 48, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial
          color={color}
          roughness={0.6}
          metalness={0.05}
          wireframe={wireframe}
          side={THREE.DoubleSide}
        />
      </mesh>
      {showMeasurements && (
        <Html center position={[0, 1.0, 0]} style={{ pointerEvents: "none" }}>
          <span className="rounded bg-amber-500/20 px-2 py-0.5 font-mono text-[10px] text-amber-100">
            placeholder · upload a capture for real geometry
          </span>
        </Html>
      )}
    </group>
  );
}

function heatColor(t: number): [number, number, number] {
  // Linear ramp through indigo → cyan → yellow → red.
  const stops: ReadonlyArray<readonly [number, readonly [number, number, number]]> = [
    [0.0, [0.10, 0.18, 0.45]],
    [0.33, [0.13, 0.66, 0.78]],
    [0.66, [0.95, 0.79, 0.18]],
    [1.0, [0.85, 0.18, 0.18]],
  ] as const;
  for (let i = 0; i < stops.length - 1; i++) {
    const a = stops[i]!;
    const b = stops[i + 1]!;
    if (t <= b[0]) {
      const u = (t - a[0]) / (b[0] - a[0]);
      return [
        a[1][0] + (b[1][0] - a[1][0]) * u,
        a[1][1] + (b[1][1] - a[1][1]) * u,
        a[1][2] + (b[1][2] - a[1][2]) * u,
      ];
    }
  }
  const last = stops[stops.length - 1]!;
  return [last[1][0], last[1][1], last[1][2]];
}

/**
 * Cheap geometry merge — only positions/normals; we recompute normals
 * after merging anyway. Avoids pulling in BufferGeometryUtils to keep
 * the bundle tighter.
 */
function mergeInto(target: THREE.BufferGeometry, src: THREE.BufferGeometry): THREE.BufferGeometry {
  const targetPos = target.getAttribute("position") as THREE.BufferAttribute | undefined;
  const srcPos = src.getAttribute("position") as THREE.BufferAttribute | undefined;
  if (!srcPos) return target;
  if (!targetPos) {
    target.setAttribute("position", srcPos.clone());
    return target;
  }
  const merged = new Float32Array(targetPos.array.length + srcPos.array.length);
  merged.set(targetPos.array as Float32Array, 0);
  merged.set(srcPos.array as Float32Array, targetPos.array.length);
  target.setAttribute("position", new THREE.BufferAttribute(merged, 3));
  return target;
}
