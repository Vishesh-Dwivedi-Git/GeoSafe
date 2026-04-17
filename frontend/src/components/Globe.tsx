"use client";

import React, { useRef, useMemo, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/* ───────────────────────────── constants ───────────────────────────── */
const GLOBE_RADIUS = 2.5;
const ATMOSPHERE_RADIUS = 2.72;
const DOT_COUNT = 12000;
const PRIMARY = new THREE.Color("#3adffa");
const PRIMARY_DIM = new THREE.Color("#1ad0eb");
const SECONDARY = new THREE.Color("#699cff");
const TERTIARY = new THREE.Color("#c890ff");

/* ───────────────────── latitude / longitude helpers ───────────────── */
function latLngToVec3(lat: number, lng: number, r: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta)
  );
}

/* ───────────────────────── dotted sphere mesh ─────────────────────── */
function DottedSphere() {
  const ref = useRef<THREE.Points>(null);

  const geometry = useMemo(() => {
    const positions = new Float32Array(DOT_COUNT * 3);
    const sizes = new Float32Array(DOT_COUNT);
    const opacities = new Float32Array(DOT_COUNT);

    for (let i = 0; i < DOT_COUNT; i++) {
      // fibonacci sphere distribution for even spread
      const y = 1 - (i / (DOT_COUNT - 1)) * 2;
      const radiusAtY = Math.sqrt(1 - y * y);
      const theta = ((Math.PI * (1 + Math.sqrt(5))) * i);

      const x = Math.cos(theta) * radiusAtY;
      const z = Math.sin(theta) * radiusAtY;

      positions[i * 3] = x * GLOBE_RADIUS;
      positions[i * 3 + 1] = y * GLOBE_RADIUS;
      positions[i * 3 + 2] = z * GLOBE_RADIUS;

      // Simulate land masses by density – points near typical land coordinates glow brighter
      const lat = Math.asin(y) * (180 / Math.PI);
      const lng = Math.atan2(z, x) * (180 / Math.PI);

      const isLandLike =
        (lat > 10 && lat < 60 && lng > -130 && lng < -60) || // North America
        (lat > -40 && lat < 15 && lng > -80 && lng < -35) || // South America
        (lat > 35 && lat < 70 && lng > -10 && lng < 60) || // Europe
        (lat > -35 && lat < 35 && lng > 10 && lng < 55) || // Africa
        (lat > 5 && lat < 55 && lng > 60 && lng < 145) || // Asia
        (lat > -45 && lat < -10 && lng > 110 && lng < 155); // Australia

      sizes[i] = isLandLike ? 2.2 + Math.random() * 1.0 : 0.8 + Math.random() * 0.4;
      opacities[i] = isLandLike ? 0.6 + Math.random() * 0.4 : 0.08 + Math.random() * 0.1;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
    geo.setAttribute("aOpacity", new THREE.BufferAttribute(opacities, 1));
    return geo;
  }, []);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        uniforms: {
          uColor: { value: PRIMARY },
          uTime: { value: 0 },
        },
        vertexShader: `
          attribute float aSize;
          attribute float aOpacity;
          varying float vOpacity;
          uniform float uTime;
          void main() {
            vOpacity = aOpacity;
            vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = aSize * (300.0 / -mvPos.z);
            gl_Position = projectionMatrix * mvPos;
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          varying float vOpacity;
          void main() {
            float d = length(gl_PointCoord - vec2(0.5));
            if (d > 0.5) discard;
            float alpha = smoothstep(0.5, 0.1, d) * vOpacity;
            gl_FragColor = vec4(uColor, alpha);
          }
        `,
      }),
    []
  );

  useFrame((_, delta) => {
    if (ref.current) {
      material.uniforms.uTime.value += delta;
    }
  });

  return <points ref={ref} geometry={geometry} material={material} />;
}

/* ───────────────────────── atmosphere glow ring ───────────────────── */
function Atmosphere() {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        side: THREE.BackSide,
        uniforms: {
          uColor: { value: PRIMARY },
        },
        vertexShader: `
          varying vec3 vNormal;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          varying vec3 vNormal;
          void main() {
            float intensity = pow(0.72 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
            gl_FragColor = vec4(uColor, intensity * 0.6);
          }
        `,
      }),
    []
  );

  return (
    <mesh material={material}>
      <sphereGeometry args={[ATMOSPHERE_RADIUS, 64, 64]} />
    </mesh>
  );
}

/* ──────────────────────── inner atmosphere haze ──────────────────── */
function InnerGlow() {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        side: THREE.FrontSide,
        uniforms: {
          uColor: { value: PRIMARY_DIM },
        },
        vertexShader: `
          varying vec3 vNormal;
          varying vec3 vPosition;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            vPosition = position;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          varying vec3 vNormal;
          void main() {
            float intensity = pow(0.55 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
            gl_FragColor = vec4(uColor, intensity * 0.35);
          }
        `,
      }),
    []
  );

  return (
    <mesh material={material}>
      <sphereGeometry args={[GLOBE_RADIUS + 0.02, 64, 64]} />
    </mesh>
  );
}

/* ─────────────────────── wireframe latitude lines ─────────────────── */
function GridLines() {
  const lineObjects = useMemo(() => {
    const objects: THREE.Line[] = [];
    const mat = new THREE.LineBasicMaterial({ color: PRIMARY, transparent: true, opacity: 0.06 });

    // Latitude lines
    for (let lat = -60; lat <= 60; lat += 30) {
      const points: THREE.Vector3[] = [];
      for (let lng = 0; lng <= 360; lng += 2) {
        points.push(latLngToVec3(lat, lng, GLOBE_RADIUS + 0.01));
      }
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      objects.push(new THREE.Line(geo, mat));
    }

    // Longitude lines
    for (let lng = 0; lng < 360; lng += 30) {
      const points: THREE.Vector3[] = [];
      for (let lat = -90; lat <= 90; lat += 2) {
        points.push(latLngToVec3(lat, lng, GLOBE_RADIUS + 0.01));
      }
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      objects.push(new THREE.Line(geo, mat));
    }

    return objects;
  }, []);

  return (
    <>
      {lineObjects.map((obj, i) => (
        <primitive key={`grid-${i}`} object={obj} />
      ))}
    </>
  );
}

/* ───────────────────────────── flying arcs ────────────────────────── */
function DataArcs() {
  const arcObjects = useMemo(() => {
    const routes: [number, number, number, number][] = [
      [40.7, -74.0, 51.5, -0.1],     // NYC → London
      [35.7, 139.7, -33.9, 151.2],   // Tokyo → Sydney
      [28.6, 77.2, 12.97, 77.59],    // Delhi → Bangalore
      [37.8, -122.4, 22.3, 114.2],   // SF → Hong Kong
      [48.9, 2.35, 55.75, 37.6],     // Paris → Moscow
      [-23.5, -46.6, 6.5, 3.4],      // São Paulo → Lagos
      [1.35, 103.8, 35.7, 139.7],    // Singapore → Tokyo
      [51.5, -0.1, 28.6, 77.2],      // London → Delhi
    ];

    const colors = [PRIMARY, SECONDARY, TERTIARY, PRIMARY_DIM, SECONDARY, PRIMARY, TERTIARY, PRIMARY_DIM];

    return routes.map(([lat1, lng1, lat2, lng2], i) => {
      const start = latLngToVec3(lat1, lng1, GLOBE_RADIUS + 0.02);
      const end = latLngToVec3(lat2, lng2, GLOBE_RADIUS + 0.02);

      const mid = new THREE.Vector3()
        .addVectors(start, end)
        .multiplyScalar(0.5)
        .normalize()
        .multiplyScalar(GLOBE_RADIUS + 0.6 + Math.random() * 0.6);

      const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
      const points = curve.getPoints(64);
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      const mat = new THREE.LineBasicMaterial({ color: colors[i % colors.length], transparent: true, opacity: 0.3 });

      return new THREE.Line(geo, mat);
    });
  }, []);

  return (
    <>
      {arcObjects.map((obj, i) => (
        <primitive key={`arc-${i}`} object={obj} />
      ))}
    </>
  );
}

/* ───────────────────── glowing city hotspot dots ──────────────────── */
function CityHotspots() {
  const cities: [number, number, string][] = [
    [40.7, -74.0, "primary"],
    [51.5, -0.1, "primary"],
    [35.7, 139.7, "secondary"],
    [28.6, 77.2, "tertiary"],
    [12.97, 77.59, "primary"],  // Bangalore (GeoSafe target)
    [-33.9, 151.2, "secondary"],
    [37.8, -122.4, "primary"],
    [22.3, 114.2, "secondary"],
    [48.9, 2.35, "primary"],
    [55.75, 37.6, "tertiary"],
    [1.35, 103.8, "secondary"],
    [-23.5, -46.6, "tertiary"],
    [6.5, 3.4, "primary"],
    [25.2, 55.3, "secondary"],
    [31.2, 121.5, "primary"],
  ];

  const colorMap: Record<string, THREE.Color> = {
    primary: PRIMARY,
    secondary: SECONDARY,
    tertiary: TERTIARY,
  };

  return (
    <>
      {cities.map(([lat, lng, colorKey], i) => {
        const pos = latLngToVec3(lat, lng, GLOBE_RADIUS + 0.03);
        const isBangalore = lat === 12.97 && lng === 77.59;
        return (
          <mesh key={`city-${i}`} position={pos}>
            <sphereGeometry args={[isBangalore ? 0.045 : 0.025, 12, 12]} />
            <meshBasicMaterial
              color={colorMap[colorKey]}
              transparent
              opacity={isBangalore ? 1.0 : 0.8}
            />
          </mesh>
        );
      })}
    </>
  );
}

/* ──────────────────── pulsing ring on target location ──────────────── */
function PulsingTarget() {
  const ringRef = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);

  const targetPos = latLngToVec3(12.97, 77.59, GLOBE_RADIUS + 0.04);

  // Calculate orientation: the ring should face outward from globe center
  const normal = targetPos.clone().normalize();
  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    return q;
  }, [normal]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (ringRef.current) {
      const scale = 1 + Math.sin(t * 2) * 0.3;
      ringRef.current.scale.set(scale, scale, scale);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.6 - Math.sin(t * 2) * 0.3;
    }
    if (ring2Ref.current) {
      const scale2 = 1 + Math.sin(t * 2 + 1) * 0.5;
      ring2Ref.current.scale.set(scale2, scale2, scale2);
      (ring2Ref.current.material as THREE.MeshBasicMaterial).opacity = 0.3 - Math.sin(t * 2 + 1) * 0.2;
    }
  });

  return (
    <>
      <mesh ref={ringRef} position={targetPos} quaternion={quaternion}>
        <ringGeometry args={[0.06, 0.08, 32]} />
        <meshBasicMaterial color={PRIMARY} transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={ring2Ref} position={targetPos} quaternion={quaternion}>
        <ringGeometry args={[0.1, 0.115, 32]} />
        <meshBasicMaterial color={PRIMARY} transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>
    </>
  );
}

/* ────────────────────────── orbiting particles ────────────────────── */
function OrbitingParticles() {
  const ref = useRef<THREE.Points>(null);

  const geometry = useMemo(() => {
    const count = 200;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = GLOBE_RADIUS + 0.3 + Math.random() * 1.2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.05;
      ref.current.rotation.x += delta * 0.02;
    }
  });

  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial
        color={PRIMARY}
        size={0.015}
        transparent
        opacity={0.4}
        sizeAttenuation
      />
    </points>
  );
}

/* ──────────────────────── main globe group ─────────────────────────── */
function GlobeScene({ speed = 0.08 }: { speed?: number }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * speed;
    }
  });

  return (
    <group ref={groupRef} rotation={[0.3, -0.5, 0.1]}>
      <DottedSphere />
      <Atmosphere />
      <InnerGlow />
      <GridLines />
      <DataArcs />
      <CityHotspots />
      <PulsingTarget />
      <OrbitingParticles />
    </group>
  );
}

/* ──────────────────────── camera auto-position ────────────────────── */
function CameraSetup({ distance = 6.5 }: { distance?: number }) {
  const { camera } = useThree();
  useMemo(() => {
    camera.position.set(0, 0.8, distance);
    camera.lookAt(0, 0, 0);
  }, [camera, distance]);
  return null;
}

/* ────────────────────────── exported component ────────────────────── */
interface GlobeProps {
  className?: string;
  speed?: number;
  cameraDistance?: number;
}

export default function Globe({
  className = "",
  speed = 0.08,
  cameraDistance = 6.5,
}: GlobeProps) {
  /* stable fallback to prevent hydration mismatches */
  const fallback = useCallback(
    () => <div className={`${className} bg-transparent`} />,
    [className]
  );

  return (
    <div className={className}>
      <Canvas
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
        dpr={[1, 2]}
        camera={{ fov: 45, near: 0.1, far: 100 }}
        style={{ background: "transparent" }}
        fallback={fallback()}
      >
        <CameraSetup distance={cameraDistance} />
        <ambientLight intensity={0.15} />
        <directionalLight position={[5, 3, 5]} intensity={0.4} color="#3adffa" />
        <GlobeScene speed={speed} />
      </Canvas>
    </div>
  );
}
