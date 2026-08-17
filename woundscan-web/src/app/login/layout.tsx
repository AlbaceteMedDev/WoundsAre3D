import type { Metadata } from "next";

/**
 * `login/page.tsx` is a client component, so its metadata has to live here.
 * The sign-in screen carries no marketing value and should stay out of search.
 */
export const metadata: Metadata = {
  title: "Portal sign in",
  alternates: { canonical: "/login" },
  robots: { index: false, follow: true },
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
