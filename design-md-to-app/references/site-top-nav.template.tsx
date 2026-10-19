import { getTranslations } from "next-intl/server";
// Locale-aware Link (references/i18n-next-intl.md). Without i18n routing, `import Link from "next/link"`.
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";

// The project's name is a brand, not copy: it is not translated. Write it once here (or import it from the
// project's site config) — never repeat the string in JSX.
const SITE = { name: "Notarius", initial: "N" };

// Hrefs are the project's main routes; labels are message keys under "SiteNav".
const NAV = [
  { href: "/", key: "dashboard" },
  { href: "/pratiche", key: "cases" },
  { href: "/clienti", key: "clients" },
  { href: "/scadenze", key: "deadlines" },
  { href: "/showcase", key: "showcase" },
] as const;

/*
 * messages/en.json                                   messages/it.json
 * "SiteNav": {                                       "SiteNav": {
 *   "dashboard": "Dashboard",                          "dashboard": "Dashboard",
 *   "cases": "Cases",                                  "cases": "Pratiche",
 *   "clients": "Clients",                              "clients": "Clienti",
 *   "deadlines": "Deadlines",                          "deadlines": "Scadenze",
 *   "showcase": "Design system",                       "showcase": "Design system",
 *   "signIn": "Sign in",                               "signIn": "Accedi",
 *   "primaryAction": "New case"                        "primaryAction": "Nuova pratica"
 * }                                                  }
 *
 * Type sizes are the theme's --text-* slots, redefined from DESIGN.md (`text-sm`), never an arbitrary `text-[…]`.
 */
export async function SiteTopNav() {
  const t = await getTranslations("SiteNav");
  return (
    <header className="border-b border-outline bg-surface">
      <div className="mx-auto max-w-[1280px] px-6 lg:px-12 h-14 flex items-center gap-8">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <div className="size-7 rounded-md bg-primary flex items-center justify-center text-surface text-xs font-semibold">
            {SITE.initial}
          </div>
          <span className="text-sm font-semibold text-on-surface">{SITE.name}</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="text-on-surface-variant hover:text-on-surface transition-colors"
            >
              {t(n.key)}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <Link href="/sign-in" className="text-sm text-on-surface-variant hover:text-on-surface">
            {t("signIn")}
          </Link>
          <Button size="sm">{t("primaryAction")}</Button>
        </div>
      </div>
    </header>
  );
}
