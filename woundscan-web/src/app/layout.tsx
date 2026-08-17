import "@/styles/globals.css";
import type { Metadata, Viewport } from "next";
import { Sora, DM_Sans, IBM_Plex_Mono } from "next/font/google";
import { ThemeBootstrap } from "@/components/theme/ThemeBootstrap";

const SITE = "https://stratametricai.com";

/**
 * One canonical description of the product, reused across search, link
 * previews and structured data. It deliberately names the whole system —
 * capture, measurement, documentation, claims, inventory, scheduling — because
 * most people meet this product by receiving the URL in a text with no other
 * context, and "3D wound measurement" alone undersells what they'd be buying.
 */
const SHARE_DESCRIPTION =
  "A 4-second iPhone LiDAR scan becomes objective 3D wound measurement — length, width, true depth and area. Documentation, claims compliance, graft inventory and scheduling run in one audit-ready portal.";

const SEARCH_DESCRIPTION =
  "AI Wound Scan turns a 4-second iPhone LiDAR scan into objective, reproducible 3D wound measurement — length, width, true depth, wound bed and peri-wound area. Audit-defensible documentation, claims compliance, UDI-traceable graft inventory, healing analytics and route planning in one portal for wound care teams.";

const sora = Sora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: {
    default: "StrataMetric — 3D Wound Measurement & Wound-Care Platform",
    template: "%s | StrataMetric",
  },
  description: SEARCH_DESCRIPTION,
  applicationName: "AI Wound Scan",
  authors: [{ name: "Albacete MedDev", url: "https://albacetemeddev.com" }],
  creator: "StrataMetric",
  publisher: "Albacete MedDev LLC",
  category: "Medical Technology",
  keywords: [
    "wound measurement",
    "3D wound scan",
    "LiDAR wound imaging",
    "wound care documentation",
    "wound care EHR",
    "CMS audit defensibility",
    "wound depth measurement",
    "graft UDI tracking",
    "wound care claims compliance",
    "StrataMetric",
    "AI Wound Scan",
    "Albacete MedDev",
  ],
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 },
  },
  openGraph: {
    title: "AI Wound Scan — 3D wound measurement & wound-care platform",
    description: SHARE_DESCRIPTION,
    siteName: "StrataMetric",
    url: SITE,
    locale: "en_US",
    type: "website",
    images: [
      {
        url: "/og-v2.png",
        width: 1200,
        height: 630,
        alt: "StrataMetric AI Wound Scan — objective 3D wound measurement in 4 seconds, with documentation, claims compliance, graft inventory and scheduling in one portal.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Wound Scan — 3D wound measurement & wound-care platform",
    description: SHARE_DESCRIPTION,
    images: ["/og-v2.png"],
  },
  appleWebApp: { capable: true, title: "AI Wound Scan", statusBarStyle: "black-translucent" },
  icons: {
    // A favicon can't read the in-page theme toggle, only the browser/OS color
    // scheme — so light UA gets the light mark, dark UA gets the navy mark.
    icon: [
      { url: "/icon-light.png", media: "(prefers-color-scheme: light)", type: "image/png" },
      { url: "/icon-dark.png", media: "(prefers-color-scheme: dark)", type: "image/png" },
    ],
    apple: [{ url: "/icon-dark.png" }],
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#05070c" },
  ],
};

/**
 * Structured data so search engines (and any unfurler that reads JSON-LD)
 * can describe the product accurately, including the capabilities that a
 * one-line preview can't carry.
 */
const STRUCTURED_DATA = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE}/#organization`,
      name: "StrataMetric",
      url: SITE,
      logo: `${SITE}/icon-dark.png`,
      description:
        "StrataMetric builds objective wound-measurement and documentation software, part of the Albacete MedDev ecosystem.",
      parentOrganization: { "@type": "Organization", name: "Albacete MedDev LLC", url: "https://albacetemeddev.com" },
    },
    {
      "@type": "WebSite",
      "@id": `${SITE}/#website`,
      url: SITE,
      name: "StrataMetric — AI Wound Scan",
      description: SEARCH_DESCRIPTION,
      publisher: { "@id": `${SITE}/#organization` },
      inLanguage: "en-US",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${SITE}/#software`,
      name: "AI Wound Scan",
      applicationCategory: "HealthApplication",
      applicationSubCategory: "Wound care measurement and documentation",
      operatingSystem: "iOS (capture), web (portal)",
      url: SITE,
      image: `${SITE}/og-v2.png`,
      description: SEARCH_DESCRIPTION,
      publisher: { "@id": `${SITE}/#organization` },
      featureList: [
        "Four-second iPhone LiDAR wound capture",
        "Objective 3D measurement: length, width, true depth, wound bed and peri-wound area",
        "Reproducible measurements with stated uncertainty",
        "Auto-generated, audit-defensible documentation",
        "Patient and wound tracking with healing trajectories",
        "Clinical notes with sign-and-lock",
        "Claims and documentation-compliance checks",
        "UDI-traceable graft inventory",
        "Reporting and analytics",
        "Route planning for mobile providers",
        "Tamper-evident audit hash chain",
      ],
      offers: { "@type": "Offer", availability: "https://schema.org/PreOrder", category: "Contact for access" },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sora.variable} ${dmSans.variable} ${plexMono.variable}`} suppressHydrationWarning>
      <head>
        <ThemeBootstrap />
        <script
          type="application/ld+json"
          // Static, developer-authored JSON — no user input is interpolated.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(STRUCTURED_DATA) }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
