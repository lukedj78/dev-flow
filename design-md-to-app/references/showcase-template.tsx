import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

// ────────────────────────────────────────────────────────────────────────────
// Brand-specific Eyebrow component (the small uppercase mono label that
// recurs on top of every section). Same pattern as airbnb-clone, aetherfield,
// devops-graphite — a spec-aware showcase always has one.
// ────────────────────────────────────────────────────────────────────────────
function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-semibold tracking-[0.32px] uppercase text-on-surface-variant">
      {children}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// COLOR — extracted directly from the Figma Variables panel of the source
// (Phoenix Legal Admin Dashboard kit). Each card: hex (mono) + name +
// short note explaining the role.
// ────────────────────────────────────────────────────────────────────────────
const COLORS = [
  { name: "primary",            hex: "#7839CD", note: "Brand purple — primary CTAs, active sidebar item",  cls: "bg-primary text-surface" },
  { name: "background-primary", hex: "#F1EEFE", note: "Active sidebar tint, primary-emphasis surfaces",     cls: "bg-background-primary text-primary border border-outline" },
  { name: "surface",            hex: "#FFFFFF", note: "Card / panel surface — most pixels on screen",       cls: "bg-surface text-on-surface border border-outline" },
  { name: "surface-bright",     hex: "#FFFFFF", note: "Pure white inside cards on cream",                   cls: "bg-surface-bright text-on-surface border border-outline" },
  { name: "hover",              hex: "#F9FAFC", note: "Imperceptible row hover — confirmation, not event",  cls: "bg-hover text-on-surface border border-outline" },
  { name: "outline",            hex: "#E4E4E4", note: "Hairline borders, dividers",                         cls: "bg-outline text-on-surface" },
  { name: "background-weak",    hex: "#E4E4E4", note: "Soft surface for skeleton states",                   cls: "bg-background-weak text-on-surface" },
  { name: "on-surface",         hex: "#474747", note: "Body text — soft black for long-reading",            cls: "bg-on-surface text-surface" },
  { name: "on-surface-variant", hex: "#959595", note: "Captions, metadata, helper copy",                    cls: "bg-on-surface-variant text-surface" },
  { name: "success",            hex: "#409261", note: "Closed / done states (firmata, archiviata)",         cls: "bg-success text-surface" },
  { name: "success-weak",       hex: "#E9FFEF", note: "Soft surface for status badges",                     cls: "bg-success-weak text-success" },
  { name: "alert",              hex: "#D98634", note: "Warning, in scadenza, pending validations",          cls: "bg-alert text-surface" },
  { name: "alert-weak",         hex: "#FFF2DD", note: "Soft surface for alert badges",                      cls: "bg-alert-weak text-alert" },
  { name: "error",              hex: "#D93434", note: "Destructive, validation errors",                     cls: "bg-error text-surface" },
  { name: "error-weak",         hex: "#FFDDDD", note: "Soft surface for error toasts",                      cls: "bg-error-weak text-error" },
];

// ────────────────────────────────────────────────────────────────────────────
// TYPOGRAPHY — Inter at every level, samples are real notarial copy
// (clienti, pratiche, atti, scadenze) so the showcase reads like a fragment
// of the product, not a generic gallery.
// ────────────────────────────────────────────────────────────────────────────
const TYPES = [
  { name: "display",     spec: "Inter · 32 / 40 · 600 · -0.01em", sample: "Buongiorno, Studio Marini",                                                                                style: { fontSize: "32px", lineHeight: "40px", letterSpacing: "-0.01em", fontWeight: 600 } },
  { name: "headline-lg", spec: "Inter · 24 / 32 · 600",            sample: "Pratiche più attive degli ultimi 7 giorni",                                                                style: { fontSize: "24px", lineHeight: "32px", fontWeight: 600 } },
  { name: "headline-md", spec: "Inter · 20 / 28 · 600",            sample: "Compravendita immobile via Roma 12",                                                                       style: { fontSize: "20px", lineHeight: "28px", fontWeight: 600 } },
  { name: "headline-sm", spec: "Inter · 16 / 24 · 600",            sample: "Cliente — Bianchi srl",                                                                                    style: { fontSize: "16px", lineHeight: "24px", fontWeight: 600 } },
  { name: "body-lg",     spec: "Inter · 16 / 24 · 400",            sample: "La pratica include atto di compravendita, accollo mutuo e cancellazione di precedente ipoteca.",          style: { fontSize: "16px", lineHeight: "24px", fontWeight: 400 } },
  { name: "body-md",     spec: "Inter · 14 / 20 · 400",            sample: "Workhorse per table rows, form helper text e contenuti densi.",                                            style: { fontSize: "14px", lineHeight: "20px", fontWeight: 400 } },
  { name: "body-sm",     spec: "Inter · 13 / 18 · 400",            sample: "P.IVA 01234567890 · 3 pratiche aperte",                                                                    style: { fontSize: "13px", lineHeight: "18px", fontWeight: 400 } },
  { name: "label-md",    spec: "Inter · 13 / 18 · 500",            sample: "Aggiornata il 12 ottobre 2026 alle 14:32",                                                                 style: { fontSize: "13px", lineHeight: "18px", fontWeight: 500 } },
  { name: "caption",     spec: "Inter · 12 / 16 · 400",            sample: "Dati protetti — segreto professionale GDPR",                                                               style: { fontSize: "12px", lineHeight: "16px", fontWeight: 400 } },
  { name: "button",      spec: "Inter · 13 / 16 · 600 · 0.04em",   sample: "Nuova pratica",                                                                                            style: { fontSize: "13px", lineHeight: "16px", letterSpacing: "0.04em", fontWeight: 600 } },
];

const RADII = [
  { name: "none", px: 0,    cls: "rounded-none" },
  { name: "sm",   px: 4,    cls: "rounded-sm" },
  { name: "md",   px: 8,    cls: "rounded-md" },
  { name: "lg",   px: 12,   cls: "rounded-lg" },
  { name: "full", px: 9999, cls: "rounded-full" },
];

const SPACING = [
  { name: "xs",  px: 4,  cls: "w-1" },
  { name: "sm",  px: 8,  cls: "w-2" },
  { name: "md",  px: 16, cls: "w-4" },
  { name: "lg",  px: 24, cls: "w-6" },
  { name: "xl",  px: 32, cls: "w-8" },
  { name: "xxl", px: 48, cls: "w-12" },
];

// ────────────────────────────────────────────────────────────────────────────
// PAGE
// ────────────────────────────────────────────────────────────────────────────
export default function Showcase() {
  return (
    <main className="bg-surface text-on-surface min-h-screen">
      {/* Header */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20">
          <div className="space-y-5">
            <Eyebrow>Notarius design system</Eyebrow>
            <h1
              style={{
                fontSize: "72px",
                lineHeight: "80px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              Quietly opinionated CRM for notary studios.
            </h1>
            <p
              className="text-on-surface-variant max-w-2xl"
              style={{ fontSize: "18px", lineHeight: "28px" }}
            >
              Generated from{" "}
              <code className="bg-hover px-1.5 py-0.5 rounded text-[14px] border border-outline">
                .workflow/DESIGN.md
              </code>{" "}
              by the{" "}
              <code className="bg-hover px-1.5 py-0.5 rounded text-[14px] border border-outline">
                design-md-to-app
              </code>{" "}
              skill. Editorial admin palette — purple primary reserved for the load-bearing
              CTA, everything else a disciplined neutrals + semantic-tints scheme.
            </p>
            <div>
              <Link
                href="/"
                className="inline-flex items-center gap-1.5 text-[14px] text-primary hover:underline"
              >
                ← Torna alla dashboard
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Colors */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Colors</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              The palette.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              15 named tokens — extracted exactly from the Figma Variables panel (no
              k-means inference). Brand purple{" "}
              <code className="bg-hover px-1 rounded text-[13px] border border-outline">
                #7839CD
              </code>{" "}
              reserved for primary CTA + active sidebar item.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {COLORS.map((c) => (
              <div
                key={c.name}
                className={`${c.cls} h-32 rounded-md p-4 flex flex-col justify-between`}
              >
                <div className="font-mono text-[12px] opacity-80">{c.hex}</div>
                <div className="space-y-1">
                  <div className="text-[14px] font-semibold">{c.name}</div>
                  <div className="text-[12px] opacity-80">{c.note}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Typography */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Typography</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              The voice.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              Single-family system —{" "}
              <strong className="text-on-surface">Inter</strong> via{" "}
              <code className="bg-hover px-1 rounded text-[13px] border border-outline">
                next/font/google
              </code>
              . 10 levels covering display headlines down to button copy. Body weight is
              400; metadata is 400 in <code>on-surface-variant</code>; buttons are 600
              with +0.04em tracking.
            </p>
          </div>
          <ul className="divide-y divide-outline">
            {TYPES.map((t) => (
              <li
                key={t.name}
                className="grid grid-cols-[140px_240px_1fr] items-baseline gap-6 py-5"
              >
                <span className="text-[14px] font-medium">{t.name}</span>
                <span className="text-[12px] tracking-wide uppercase text-on-surface-variant">
                  {t.spec}
                </span>
                <span style={t.style}>{t.sample}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Buttons */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Buttons</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              One purple primary per viewport.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              Reserve the brand purple <code>#7839CD</code> for the single most important
              action on each screen — its job is wayfinding, not decoration.
            </p>
          </div>
          <div className="flex flex-wrap gap-4 items-center">
            <Button>Nuova pratica</Button>
            <Button variant="outline">Filtra pratiche</Button>
            <Button variant="secondary">Esporta CSV</Button>
            <Button variant="ghost">Vedi storico</Button>
            <Button variant="link">Termini di servizio</Button>
            <Button variant="destructive">Annulla pratica</Button>
            <Button disabled>Salva</Button>
          </div>
        </div>
      </section>

      {/* Cards & Containers */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Cards & containers</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              Flat by design, hierarchy via tonal layers.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              Surface (#FFFFFF) on hover-weak background; primary-tinted lavender
              (#F1EEFE) for active states; hairline outline (#E4E4E4) carries the
              divisions. Shadows reserved for popovers/modals only.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Practice card — dashboard widget */}
            <Card className="rounded-md p-6 space-y-3">
              <CardHeader className="p-0">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-[16px] font-semibold">
                    Compravendita Bianchi → Rossi
                  </CardTitle>
                  <Badge className="bg-success-weak text-success border-success/20 text-[10px]">
                    Firmata
                  </Badge>
                </div>
                <CardDescription className="text-[12px] text-on-surface-variant mt-1 font-mono">
                  Pratica 2026-117 · atto del 12/04/2026
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0 space-y-2 text-[14px] text-on-surface-variant pt-3 border-t border-outline">
                <div className="flex justify-between">
                  <span>Tipo</span>
                  <span className="text-on-surface font-medium">Compravendita</span>
                </div>
                <div className="flex justify-between">
                  <span>Parti</span>
                  <span className="text-on-surface font-medium">2 soggetti</span>
                </div>
                <div className="flex justify-between">
                  <span>Documenti</span>
                  <span className="text-on-surface font-medium">14 file</span>
                </div>
              </CardContent>
            </Card>

            {/* At-risk callout — primary tonal layer */}
            <Card className="rounded-md p-6 space-y-3 bg-background-primary border-primary/20">
              <Eyebrow>Pratiche a rischio</Eyebrow>
              <p
                className="text-on-surface"
                style={{ fontSize: "20px", lineHeight: "28px", fontWeight: 600 }}
              >
                4 pratiche richiedono attenzione nei prossimi 3 giorni.
              </p>
              <div className="text-[14px] text-on-surface-variant pt-3 border-t border-outline space-y-1.5">
                <div>2026-118 · documento antiriciclaggio mancante</div>
                <div>2026-114 · inattiva da 18 giorni</div>
                <div>2026-103 · voltura catastale rifiutata</div>
              </div>
            </Card>

            {/* Client card — surface bright on cream */}
            <Card className="rounded-md p-6 space-y-3 bg-surface-bright">
              <CardHeader className="p-0">
                <CardTitle className="text-[18px] font-semibold">Bianchi srl</CardTitle>
                <CardDescription className="text-[14px] font-mono">
                  P.IVA 01234567890
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0 space-y-2 text-[14px] text-on-surface-variant pt-3 border-t border-outline">
                <div className="flex justify-between">
                  <span>Pratiche aperte</span>
                  <span className="text-on-surface font-medium">3</span>
                </div>
                <div className="flex justify-between">
                  <span>Ultima attività</span>
                  <span className="text-on-surface font-medium">2 giorni fa</span>
                </div>
                <div className="flex justify-between">
                  <span>Cliente da</span>
                  <span className="text-on-surface font-medium">2018</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Inputs */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Inputs & forms</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              Quiet input fields.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              Hairline border, 4px radius, 11–12px uppercase mono labels. Inline error
              messages in <code>error</code> red.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6 max-w-2xl">
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium tracking-wide uppercase text-on-surface-variant">
                Cliente
              </label>
              <Input
                className="rounded-sm h-11 px-4 border-outline"
                defaultValue="Bianchi srl"
                readOnly
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium tracking-wide uppercase text-on-surface-variant">
                Data prevista atto
              </label>
              <Input
                type="date"
                className="rounded-sm h-11 px-4 border-outline"
                defaultValue="2026-05-12"
                readOnly
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <label className="text-[12px] font-medium tracking-wide uppercase text-error">
                Codice fiscale (con errore)
              </label>
              <Input
                className="rounded-sm h-11 px-4 border-error focus-visible:ring-error/30"
                defaultValue="VRDMRA80"
                readOnly
              />
              <p className="text-[12px] text-error">
                Il codice fiscale deve essere lungo 16 caratteri.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Badges */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Badges</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              Status pills.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              Soft <code>*-weak</code> backgrounds with strong-color text.
              One badge per row tells the user where the practice stands at a glance.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <Badge className="bg-success-weak text-success border-success/20">
              Firmata
            </Badge>
            <Badge className="bg-background-primary text-primary border-primary/20">
              In corso
            </Badge>
            <Badge className="bg-alert-weak text-alert border-alert/20">
              In scadenza
            </Badge>
            <Badge className="bg-error-weak text-error border-error/20">
              Errore validazione
            </Badge>
            <Badge className="bg-hover text-on-surface-variant border-outline">
              Bozza
            </Badge>
            <Badge className="bg-on-surface text-surface">Archiviata</Badge>
            <Badge variant="outline">Outline default</Badge>
            <Badge>Default</Badge>
          </div>
        </div>
      </section>

      {/* Radius scale */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Radius</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              Conservative radii.
            </h2>
            <p className="text-on-surface-variant" style={{ fontSize: "16px" }}>
              4px on inputs and buttons; 8px on cards; 12px reserved for dialog
              containers; <code>full</code> for avatars and circular icons.
            </p>
          </div>
          <div className="flex flex-wrap gap-6">
            {RADII.map((r) => (
              <div key={r.name} className="space-y-2">
                <div
                  className={`${r.cls} size-24 bg-hover border border-outline flex items-center justify-center`}
                >
                  <span className="text-[12px] text-on-surface-variant">
                    {r.px === 9999 ? "∞" : `${r.px}px`}
                  </span>
                </div>
                <div className="text-[12px] tracking-wide uppercase text-on-surface-variant">
                  {r.name}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Spacing scale */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>Spacing</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              8px rhythm + 4px half-step.
            </h2>
          </div>
          <ul className="space-y-3">
            {SPACING.map((s) => (
              <li
                key={s.name}
                className="grid grid-cols-[80px_60px_1fr] items-center gap-4"
              >
                <span className="text-[14px] font-medium">{s.name}</span>
                <span className="text-[12px] tracking-wide uppercase text-on-surface-variant">
                  {s.px}px
                </span>
                <div className={`${s.cls} h-3 bg-on-surface rounded-sm`} />
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Do's and Don'ts (verbatim from DESIGN.md) */}
      <section className="border-b border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-20 space-y-10">
          <div className="space-y-3">
            <Eyebrow>From the DESIGN.md</Eyebrow>
            <h2
              style={{
                fontSize: "48px",
                lineHeight: "56px",
                letterSpacing: "-0.02em",
                fontWeight: 600,
              }}
            >
              Do&apos;s and Don&apos;ts.
            </h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            <Card className="rounded-md p-8 bg-surface-bright">
              <h3
                className="text-on-surface mb-4"
                style={{ fontSize: "16px", fontWeight: 600 }}
              >
                DO
              </h3>
              <ul className="space-y-3 text-[15px] text-on-surface-variant list-none">
                <li>
                  Reserve <strong className="text-on-surface">brand purple</strong>{" "}
                  <code>#7839CD</code> for the primary CTA per screen and the active sidebar item.
                </li>
                <li>
                  Maintain near-black-on-cream contrast for body copy. The combination of{" "}
                  <code>#474747</code> on <code>#FFFFFF</code> gives ~17:1 contrast (AAA).
                </li>
                <li>
                  Keep the cool gray <code>#F9FAFC</code> hover state imperceptible — it&apos;s a
                  confirmation signal, not a visual event.
                </li>
                <li>
                  Use <code>*-weak</code> pair colors only for chip/badge backgrounds, never
                  for typography or icons.
                </li>
              </ul>
            </Card>
            <Card className="rounded-md p-8 bg-surface-bright">
              <h3
                className="text-on-surface mb-4"
                style={{ fontSize: "16px", fontWeight: 600 }}
              >
                DON&apos;T
              </h3>
              <ul className="space-y-3 text-[15px] text-on-surface-variant list-none">
                <li>
                  Don&apos;t introduce a third saturated accent. The semantic palette
                  (success/alert/error) is the only competition allowed.
                </li>
                <li>
                  Don&apos;t add drop shadows to cards. The flat tonal-layer elevation is
                  intentional — shadows are reserved for modals/popovers.
                </li>
                <li>
                  Don&apos;t use pure <code>#000000</code> for text. The 8% softening of{" "}
                  <code>#474747</code> makes a visible difference in long-reading sessions.
                </li>
                <li>
                  Don&apos;t mix radii within a single screen. 4px (buttons/inputs), 8px
                  (cards), 9999px (avatars) — and that&apos;s it.
                </li>
              </ul>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-outline">
        <div className="mx-auto max-w-[1280px] px-6 lg:px-12 py-10 text-center font-mono text-[12px] tracking-wide uppercase text-on-surface-variant">
          Generated from .workflow/DESIGN.md · See registry.json + .workflow/screenshots
        </div>
      </footer>
    </main>
  );
}
