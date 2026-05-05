import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { CaptureHandoff } from "@/components/portal/boards/CaptureHandoff";

export default async function CaptureHandoffPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Capture handoff"
      subtitle="Take the photo on your phone, analyse on this computer."
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <CaptureHandoff />
    </AppShell>
  );
}
