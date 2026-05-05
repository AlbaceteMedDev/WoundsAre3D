import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { OrdersBoard } from "@/components/portal/boards/OrdersBoard";

export default async function OrdersPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Orders"
      subtitle="Manage product supplies, graft inventory, and shipment-tracked fulfillment."
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <OrdersBoard />
    </AppShell>
  );
}
