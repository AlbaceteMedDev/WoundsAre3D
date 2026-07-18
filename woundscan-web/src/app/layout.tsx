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
  metadataBase: new URL("https://stratametricai.com"),
  alternates: { canonical: "/" },
  title: {
    default: "StrataMetric — AI Wound Scan | Albacete MedDev",
    template: "%s | StrataMetric",
  },
  description:
    "AI Wound Scan by StrataMetric, part of the Albacete MedDev ecosystem: objective, reproducible 3D wound measurement from an iPhone LiDAR scan. Length, width, depth, wound bed and peri-wound area — audit-defensible documentation in minutes.",
  keywords: [
    "wound measurement",
    "3D wound scan",
    "LiDAR wound imaging",
    "wound care documentation",
    "CMS audit defensibility",
    "wound depth measurement",
    "StrataMetric",
    "AI Wound Scan",
    "Albacete MedDev",
  ],
  openGraph: {
    title: "StrataMetric — AI Wound Scan",
    description:
      "Objective, reproducible 3D wound measurement from an iPhone LiDAR scan. The full three-dimensional wound profile — captured at the point of care.",
    siteName: "StrataMetric",
    url: "https://stratametricai.com",
    type: "website",
    images: [{ url: "/logo-square.png", width: 1024, height: 1024 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "StrataMetric — AI Wound Scan",
    description:
      "Objective, reproducible 3D wound measurement from an iPhone LiDAR scan, by Albacete MedDev.",
  },
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
