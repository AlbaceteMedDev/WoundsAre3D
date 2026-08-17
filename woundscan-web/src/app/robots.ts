import type { MetadataRoute } from "next";

/**
 * The marketing pages are public; everything behind the portal (and the
 * signed-in surfaces) is kept out of the index.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/login", "/logout", "/dashboard", "/patients", "/wounds", "/notes", "/orders", "/reports", "/routes", "/settings", "/admin", "/m/"],
    },
    sitemap: "https://stratametricai.com/sitemap.xml",
    host: "https://stratametricai.com",
  };
}
