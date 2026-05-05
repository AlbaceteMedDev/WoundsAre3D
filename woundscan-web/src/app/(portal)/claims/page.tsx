import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { ClaimsBoard } from "@/components/portal/boards/ClaimsBoard";

export default async function ClaimsPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Claims"
      subtitle="Revenue cycle intelligence and reimbursement optimisation."
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <ClaimsBoard />
    </AppShell>
  );
}
