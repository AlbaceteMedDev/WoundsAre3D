import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "WoundScan",
  description: "WoundScan clinical decision support dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
