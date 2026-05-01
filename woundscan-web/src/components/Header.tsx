import Link from "next/link";
import { getSession } from "@/lib/auth";

export async function Header() {
  const session = await getSession();
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between p-4">
        <Link href="/" className="text-lg font-semibold text-brand-700">
          WoundScan
        </Link>
        {session && (
          <nav className="flex gap-4 text-sm">
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/wounds">Wounds</Link>
            <Link href="/phantom">Phantom</Link>
            {session.role === "admin" && (
              <>
                <Link href="/admin/products">Products</Link>
                <Link href="/admin/audit">Audit log</Link>
                <Link href="/admin/ml">ML</Link>
              </>
            )}
            <Link href="/logout">Sign out</Link>
          </nav>
        )}
      </div>
    </header>
  );
}
