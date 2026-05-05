import "@/styles/globals.css";
import type { Metadata } from "next";
import { Sora, DM_Sans } from "next/font/google";
import { ThemeBootstrap } from "@/components/theme/ThemeBootstrap";

const sora = Sora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "WoundScan — Albacete MedDev",
  description:
    "Provider portal for WoundScan: 3D wound capture, progression tracking, UDI-traceable graft applications, and Medicare reimbursement estimates.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sora.variable} ${dmSans.variable}`} suppressHydrationWarning>
      <head>
        <ThemeBootstrap />
      </head>
      <body>{children}</body>
    </html>
  );
}
