import { MobileCapture } from "@/components/mobile/MobileCapture";

export const dynamic = "force-dynamic";

export default function MobileCapturePage({ params }: { params: { id: string } }) {
  return <MobileCapture sessionId={params.id} />;
}
