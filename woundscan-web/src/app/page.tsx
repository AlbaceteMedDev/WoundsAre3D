import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import { Hero } from "@/components/marketing/Hero";
import { StatsBand } from "@/components/marketing/StatsBand";
import { AtAGlanceSection } from "@/components/marketing/AtAGlanceSection";
import { ProblemSection } from "@/components/marketing/ProblemSection";
import { PipelineSection } from "@/components/marketing/PipelineSection";
import { ReportSection } from "@/components/marketing/ReportSection";
import { DemoSection } from "@/components/marketing/DemoSection";
import { PortalTourSection } from "@/components/marketing/PortalTourSection";
import { TechnologySection } from "@/components/marketing/TechnologySection";
import { ArchitectureSection } from "@/components/marketing/ArchitectureSection";
import { PartnershipSection } from "@/components/marketing/PartnershipSection";
import { ComplianceSection } from "@/components/marketing/ComplianceSection";
import { BenefitsSection } from "@/components/marketing/BenefitsSection";
import { CtaSection } from "@/components/marketing/CtaSection";
import { Footer } from "@/components/marketing/Footer";

/**
 * Public marketing site for StrataMetric AI Wound Scan (Albacete MedDev).
 * Authenticated users skip straight to the portal dashboard.
 */
export const metadata: Metadata = { alternates: { canonical: "/" } };

export default async function HomePage() {
  const session = await getSession();
  if (session) redirect("/dashboard");

  return (
    <>
      <MarketingNav />
      <main>
        <Hero />
        <StatsBand />
        <AtAGlanceSection />
        <ProblemSection />
        <PipelineSection />
        <ReportSection />
        <DemoSection />
        <PortalTourSection />
        <TechnologySection />
        <ArchitectureSection />
        <PartnershipSection />
        <ComplianceSection />
        <BenefitsSection />
        <CtaSection />
      </main>
      <Footer />
    </>
  );
}
