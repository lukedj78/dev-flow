import { getTranslations } from "next-intl/server";
// Locale-aware Link (references/i18n-next-intl.md). Without i18n routing, `import Link from "next/link"`.
import { Link } from "@/i18n/navigation";

// The project's name is a brand, not copy: it is not translated. Write it once (or import the site config).
const SITE = { name: "Notarius" };

const COLUMNS = [
  { key: "product", links: [{ href: "/", key: "dashboard" }, { href: "/pratiche", key: "cases" }, { href: "/clienti", key: "clients" }] },
  { key: "resources", links: [{ href: "/showcase", key: "showcase" }, { href: "/sign-in", key: "signIn" }, { href: "/legal/privacy", key: "privacy" }] },
] as const;

/*
 * Brand-iconic footer for showcase / marketing-style pages: the project's name, lowercase and big enough to BE the
 * footer, between a meta row and a legal row.
 *
 * messages/en.json                                    messages/it.json
 * "SiteFooter": {                                     "SiteFooter": {
 *   "description": "A modern CRM for notary            "description": "CRM moderno per studi notarili:
 *     practices: clients, cases, deadlines and           clienti, pratiche, scadenze e archivio
 *     archive in one view.",                             in un'unica vista.",
 *   "columns": { "product": "Product",                  "columns": { "product": "Prodotto",
 *                "resources": "Resources" },                         "resources": "Risorse" },
 *   "links": { "dashboard": "Dashboard",                "links": { "dashboard": "Dashboard",
 *     "cases": "Cases", "clients": "Clients",             "cases": "Pratiche", "clients": "Clienti",
 *     "showcase": "Design system",                        "showcase": "Design system",
 *     "signIn": "Sign in",                                "signIn": "Accedi",
 *     "privacy": "Privacy" },                             "privacy": "Privacy" },
 *   "legal": "© {year} {name} · Hosted in the EU"       "legal": "© {year} {name} · Ospitato nell'UE"
 * }                                                   }
 *
 * No generator signature here: this is the client's page. Provenance lives in _design-md-mapping.json and /showcase.
 * Type sizes are the theme's --text-* slots (redefined from DESIGN.md), never text-[Npx] or an inline fontSize.
 */
export async function WordmarkFooter() {
  const t = await getTranslations("SiteFooter");
  return (
    <footer className="bg-background-primary text-primary border-t border-outline">
      <div className="mx-auto max-w-[1280px] px-6 lg:px-12 pt-16 pb-10 space-y-10">
        {/* Meta row */}
        <div className="flex flex-wrap items-start justify-between gap-6 text-sm">
          <p className="text-on-surface max-w-md">{t("description")}</p>
          <div className="flex flex-wrap gap-x-10 gap-y-3 text-on-surface-variant">
            {COLUMNS.map((col) => (
              <div key={col.key} className="space-y-2">
                <p className="font-semibold text-on-surface">{t(`columns.${col.key}`)}</p>
                {col.links.map((l) => (
                  <Link key={l.href} href={l.href} className="block hover:text-primary">
                    {t(`links.${l.key}`)}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Wordmark — the largest slots of the scale; it spans the container on desktop */}
        <div className="overflow-hidden" aria-hidden="true">
          <div className="text-7xl sm:text-8xl lg:text-9xl font-semibold text-primary leading-none tracking-tighter select-none">
            {SITE.name.toLowerCase()}
          </div>
        </div>

        {/* Legal row */}
        <div className="pt-6 border-t border-primary/20 text-xs text-on-surface-variant">
          {t("legal", { year: new Date().getFullYear(), name: SITE.name })}
        </div>
      </div>
    </footer>
  );
}
