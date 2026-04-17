import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "GEOSAFE | Hercules Platform",
  description:
    "AI-Powered Land Risk Intelligence. From coordinates to compliance in seconds. Analyze orbital datasets with hyper-local intelligence for mission-critical land decisions.",
  keywords: ["GeoSafe", "land risk", "AI", "satellite", "compliance", "spatial intelligence"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className="min-h-screen bg-black text-on-background antialiased"
        style={{
          fontFamily:
            "Inter, Space Grotesk, Segoe UI, system-ui, -apple-system, sans-serif",
        }}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
