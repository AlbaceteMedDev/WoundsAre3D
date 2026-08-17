import type { MetadataRoute } from "next";

const SITE = "https://stratametricai.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    { url: SITE, lastModified, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE}/demo`, lastModified, changeFrequency: "monthly", priority: 0.8 },
  ];
}
