import Link from "next/link";
import { Button } from "@/components/ui/button";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/pratiche", label: "Pratiche" },
  { href: "/clienti", label: "Clienti" },
  { href: "/scadenze", label: "Scadenze" },
  { href: "/showcase", label: "Showcase" },
];

export function SiteTopNav() {
  return (
    <header className="border-b border-outline bg-surface">
      <div className="mx-auto max-w-[1280px] px-6 lg:px-12 h-14 flex items-center gap-8">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <div className="size-7 rounded-md bg-primary flex items-center justify-center text-surface text-[13px] font-semibold">
            N
          </div>
          <span className="text-[14px] font-semibold text-on-surface">Notarius</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-[14px]">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="text-on-surface-variant hover:text-on-surface transition-colors"
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <Link
            href="/sign-in"
            className="text-[14px] text-on-surface-variant hover:text-on-surface"
          >
            Accedi
          </Link>
          <Button size="sm">Nuova pratica</Button>
        </div>
      </div>
    </header>
  );
}
