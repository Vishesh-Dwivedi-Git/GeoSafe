"use client";

import { GeoSafeProvider } from "@/context/GeoSafeContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return <GeoSafeProvider>{children}</GeoSafeProvider>;
}
