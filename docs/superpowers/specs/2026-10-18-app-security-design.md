# `app-security` — il quinto controllo prima del deploy: la sicurezza del codice dell'app — 2026-10-18

Secondo punto della roadmap uscita dal confronto con *The Founder's Playbook*
(`2026-10-17-founder-intelligence-design.md`, §Confronto). Il PDF chiede una revisione di sicurezza prima che
un utente tocchi il prodotto. Deve coprire:
- l'autenticazione e la gestione delle sessioni;
- i dati esposti nelle risposte delle API;
- la validazione degli input e le injection;
- le dipendenze con vulnerabilità note.

dev-flow oggi non ne fa nessuna. I quattro controlli prima del deploy guardano altro:
- `compliance-audit`: la legge;
- `vercel-doctor`: i costi;
- `shadscan`: l'interfaccia;
- `launch-audit`: se un estraneo trova il prodotto, se ne fida e se compra.

L'unica cosa di sicurezza che c'è è la soglia minima di versione di Next.js contro le CVE, dentro `vercel-deploy`.

## Fatti verificati (2026-10-18)

- **Next.js**, guida *Data Security* (aggiornata il 2026-10-06):
  - ogni Server Action esportata si può chiamare con un POST diretto, quindi autenticazione **e** autorizzazione
    vanno controllate dentro ogni action, e un controllo nella pagina non copre le action definite lì;
  - i controlli di proprietà dell'oggetto evitano l'IDOR;
  - ogni input va validato: FormData, `params`, `searchParams`, header;
  - le action devono restituire valori minimi, mai righe intere del database;
  - il modello raccomandato è un *Data Access Layer* con `import 'server-only'`;
  - le API di *taint* sono ancora sperimentali in Next 16;
  - la documentazione del proxy (`proxy.ts`, ex middleware) avverte che cambiare un matcher può togliere la
    copertura senza che nessuno se ne accorga, e la CVE-2025-29927 ha mostrato che il middleware non è un
    confine di sicurezza.
- **Variabili d'ambiente**: tutto ciò che inizia con `NEXT_PUBLIC_` finisce nel client; `EXPO_PUBLIC_` finisce
  in chiaro nel bundle dell'app.
- **Strumenti**, nessuno dei quali è installato su questa macchina:
  - **OSV-Scanner** 2.7.0 (Apache-2.0): legge direttamente `pnpm-lock.yaml` e `package-lock.json`. Exit code
    documentati: 0 pulito, 1 vulnerabilità, 127 errore, 128 nessun pacchetto. Funziona offline dopo aver
    scaricato il database.
  - **gitleaks** 8.30.1 (MIT): `gitleaks dir .` per i file, `gitleaks git .` per la cronologia, `--redact`.
    `detect` e `protect` sono deprecati. È in sola manutenzione di sicurezza.
  - **Semgrep CE** 1.180.0: esistono `p/javascript`, `p/typescript`, `p/react` e `p/nextjs`, senza login, e va
    usato con `--metrics off`. La **licenza delle regole vieta di ridistribuirle o di offrirle come
    servizio**: si scaricano al momento, mai dentro la skill.
  - **`pnpm audit` e `npm audit`**: già disponibili, ma richiedono la rete.
- **Claude Code**: il comando integrato `/security-review` rivede solo la diff del branch rispetto al branch
  principale, e richiede un remote `origin`. La GitHub Action ufficiale costa a ogni esecuzione e, per sua
  stessa ammissione, non è protetta dalla prompt injection.
- **Su questa macchina**: la skill `cso` (audit di sicurezza, OWASP Top 10, STRIDE) e il plugin
  `security-guidance` (rivede le modifiche al codice); `claude-security` è nel marketplace, non installato.
  Nessuna di queste è parte di dev-flow, quindi non ci si può contare in un altro ambiente.
- **Strix** (`strix-agent` 1.7.0 su PyPI, Apache-2.0, segnalato dall'utente):
  - test dinamico con agenti che attaccano l'app avviata dentro Docker;
  - un problema è segnalato solo se c'è un exploit che funziona;
  - serve una chiave API di un fornitore di modelli e ogni scansione costa token;
  - va usato solo su sistemi propri.
- **Nel repo**:
  - `module-add/references/module-auth.md` definisce `getSession()` e `getCurrentUserId()` in
    `lib/auth-server.ts`, e dice che il proxy non è mai il controllo di autorizzazione, ma non ha una regola di
    proprietà per oggetto;
  - `eve-agent` ha già le sue difese (approvazioni, guard, identità dalla sessione e non dal modello).
- **OWASP**: Top 10:2025 (A01 Broken Access Control, A03 Software Supply Chain Failures, A05 Injection…),
  ASVS 5.0.0, API Security Top 10 2023 (API1: BOLA, l'IDOR delle API).

## Intento

Un quinto controllo prima del deploy, `app-security`, che risponde a una domanda che nessun altro pone:
**questo codice si può attaccare?** Nella stessa forma degli altri quattro: segnala e rimanda, non blocca mai,
registra in `meta.json`, gira in qualsiasi momento e viene proposto a `feature_complete` e dopo ogni modifica
rilevante.

## Obiettivi

1. Dipendenze vulnerabili, segreti nel codice e nella cronologia, e i rischi specifici di Next.js (autorizzazione
   nelle action e nelle route, IDOR, dati esposti, segreti nelle variabili pubbliche) controllati prima di ogni
   deploy.
2. Gli strumenti si usano se ci sono; se mancano, il controllo lo dice e propone come installarli, senza mai far
   passare per «pulito» quello che non ha potuto guardare.
3. Una lettura del codice guidata, sui punti che nessuno scanner vede: autorizzazione per oggetto, dati esposti.
4. Un livello dinamico facoltativo, con Strix, per chi vuole una prova vera prima del lancio pubblico.
5. Nessuna regola o codice di terzi ridistribuito dentro la skill.

## Non obiettivi

- Un penetration test di default: è il livello dinamico, solo su richiesta.
- Correggere tutto in automatico: la skill segnala e propone; le correzioni le fanno le skill che possiedono il
  codice, o l'agente con l'utente.
- Conformità SOC 2 o ISO 27001, WAF, protezione a runtime.
- Sostituire `compliance-audit`: la legge resta lì. Qui c'è solo la parte tecnica.

## Anti-obiettivi

- Un report pieno di falsi allarmi, che smette di essere letto.
- Un «tutto a posto» quando lo strumento non c'era o non aveva la rete.
- Lanciare exploit contro sistemi che non sono dell'utente, o contro la produzione con dati reali.
- Scrivere le regole di Semgrep nella skill (lo vieta la loro licenza).

## Il design

### 1. Tre livelli

| Livello | Cosa | Con cosa | Quando |
|---|---|---|---|
| **scan** | dipendenze, segreti, analisi statica, controlli Next.js | OSV-Scanner (oppure `pnpm audit` / `npm audit`), gitleaks, Semgrep con le regole scaricate al momento, e un nostro scanner stdlib per i punti Next.js | sempre, a ogni esecuzione |
| **review** | autorizzazione per oggetto, dati esposti, input, configurazione dell'auth, header | una checklist che l'agente segue leggendo il codice, su OWASP Top 10:2025 e sulla guida *Data Security* di Next.js | sempre, sui file che lo scan indica e su tutte le action e route |
| **dynamic** | exploit veri contro l'app avviata | Strix, in Docker, contro `next start` in locale o una preview, con un utente di prova | solo su richiesta: prima del primo lancio pubblico, con dati sensibili o pagamenti |

### 2. Lo scanner (`app-security/scripts/scan_security.py`)

Stdlib, sul modello dello scanner di `compliance-audit`: produce segnali da verificare leggendo il codice, non
verdetti.

- **Strumenti esterni**, usati se presenti:
  - dipendenze: `osv-scanner scan source -r . --format json`, altrimenti `pnpm audit --json --prod` o
    `npm audit --json --omit=dev`;
  - segreti: `gitleaks dir . --redact -f json` e `gitleaks git . --redact -f json`;
  - Semgrep: `semgrep scan --config p/nextjs --config p/typescript --metrics off --json`.

  Ognuno riporta tre esiti distinti: trovato, pulito, **non controllato** (strumento assente, rete assente,
  errore). Un'esecuzione senza nessuno strumento non dice mai «pulito».
- **Controlli propri per Next.js**, euristici e dichiarati come tali:
  - un `"use server"` esportato senza chiamata a una funzione di sessione (`getSession`, `getCurrentUserId`,
    `auth(`, o quelle che il progetto dichiara) nel corpo;
  - una route `route.ts` con un handler `POST`/`PUT`/`PATCH`/`DELETE` senza controllo di sessione;
  - una query Drizzle che filtra per id preso dall'input (`eq(…id, …)`) senza un filtro su utente o tenant nella
    stessa `where`;
  - una action che restituisce il risultato di `.returning()` o una riga intera;
  - variabili `NEXT_PUBLIC_` o `EXPO_PUBLIC_` con `SECRET`, `PRIVATE`, `TOKEN` o `PASSWORD` nel nome, con
    un'eccezione per le chiavi pubbliche per natura (publishable, anon);
  - file sotto `lib/server/` o `lib/db/` senza `import "server-only"`;
  - `sql.raw` o template SQL costruiti con concatenazione;
  - nessun header di sicurezza o CSP configurato.
- **Output**: lo stesso formato di `launch-audit` (stato, dettaglio, file, a chi rimandare) e `--json`.

### 3. La checklist di revisione (`references/review.md`)

Ordinata come OWASP Top 10:2025, con per ogni voce cosa guardare nel codice di uno stack dev-flow, l'esempio
giusto e quello sbagliato. Le voci principali:

- **A01, accesso.** Ogni action e route controlla la sessione **e** che l'oggetto appartenga all'utente o al suo
  tenant, nel proprio corpo. Proxy, layout e pagina non contano. Il modello è il *Data Access Layer* di Next.js
  sopra gli helper di `module-auth` (`getCurrentUserId()`).
- **A02, configurazione.** Header di sicurezza, CSP, `trustedOrigins` e cookie di better-auth.
- **A03, catena di fornitura.** Lo scan delle dipendenze; per i componenti di terzi rimanda a `registry-intake`.
- **A05, injection.** Validazione con Zod di FormData, `params` e `searchParams`; niente SQL concatenato.
- **A07, autenticazione.** Sessioni, reset della password, rate limit sul login.
- **Dati esposti.** Le props passate ai componenti `"use client"` e i valori restituiti dalle action contengono
  solo il necessario; nessun segreto nelle variabili pubbliche.
- **Mobile (Expo).** Token in `expo-secure-store`, mai in AsyncStorage; niente segreti in `EXPO_PUBLIC_`.
- **Agenti eve.** Rimanda alle difese di `eve-agent` (approvazioni, guard), già documentate là.

### 4. Il livello dinamico con Strix

- Solo su richiesta esplicita, e solo contro l'app dell'utente: `next start` in locale o una preview, mai la
  produzione con dati reali. La skill lo dice prima di partire e chiede conferma.
- Prerequisiti: Docker in esecuzione, una chiave API di un fornitore di modelli (Strix non usa l'abbonamento
  Claude), `pipx install strix-agent`, non lo script `curl | bash`.
- Grey-box: un utente di prova creato apposta, passato con `--instruction`, così Strix prova l'IDOR tra due
  account.
- I risultati di Strix entrano nello stesso report, marcati come «dimostrati».
- Una riga in `dev-flow/references/resources.md` registra Strix: prezzo, cosa fa, limiti.

### 5. Lo stato: `meta.json#security`

```json
"security": {
  "last_run_at": "<ISO-8601 UTC>",
  "tools": { "deps": "osv-scanner | pnpm-audit | npm-audit | not-run", "secrets": "gitleaks | not-run",
             "static": "semgrep | not-run" },
  "findings": { "open": 3, "fixed": 5, "accepted": [{ "check": "…", "reason": "…" }] },
  "dynamic": { "ran_at": "…", "tool": "strix", "proven": 1 } | null
}
```

Mai `phase`, sempre una voce nella history. `accepted` registra con il motivo un rischio che l'utente decide di
tenere.

### 6. Dove entra nel flusso

È il quinto controllo, accanto agli altri quattro:

- `dev-flow/SKILL.md`: la riga `feature_complete` per web, monorepo ed Expo (per Expo valgono dipendenze,
  segreti e la parte mobile della checklist), il ciclo di manutenzione dopo `deployed`, l'elenco dei controlli e
  la frase «nessuno sostituisce l'altro».
- `show_state.py`: le stesse righe.
- `vercel-deploy`, passo 2: legge cinque blocchi invece di quattro; la soglia CVE di Next.js resta lì, perché
  riguarda la versione, e `app-security` la cita.
- `rn-eas-deploy`: una riga nella checklist.
- `dev-flow/references/policies.md`: un paragrafo per il quinto controllo.
- `spec-review`: l'elenco di ciò che salta perché lo coprono i controlli.
- Tutti i testi che dicono «quattro controlli» passano a cinque.

### 7. Quando gli strumenti mancano

La skill non installa niente da sola. Se mancano, propone il comando (`brew install osv-scanner gitleaks`,
`pipx install semgrep`) e chiede conferma. Senza strumenti fa comunque i controlli propri e la checklist, e
segnala come «non controllati» dipendenze e segreti. Per le dipendenze, `pnpm audit` / `npm audit` è il ripiego
quando c'è la rete.

## Test

- **Scanner**, con fixture in cartelle temporanee:
  - ogni controllo proprio trova il caso vero e tace sul caso giusto. Per esempio un'action con
    `getCurrentUserId()` non è segnalata; una query con `and(eq(t.id, id), eq(t.userId, uid))` non è segnalata;
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` non è segnalata;
  - un monorepo con l'app in `apps/web` viene trovato.
- **Strumenti assenti**: con un `PATH` vuoto, lo scanner riporta «non controllato» e mai «pulito».
- **Strumenti presenti**: l'interpretazione dell'output è testata su output JSON registrati (OSV-Scanner,
  gitleaks, Semgrep, pnpm audit), senza eseguire gli strumenti in CI.
- **Una prova a mano** su un progetto reale, con gli strumenti installati se l'utente dà il via.
- Il lint, i bundle, tutte le suite.

## Lasciato a chi costruisce

- La forma esatta dei messaggi e dei rimandi.
- L'elenco preciso delle funzioni di sessione riconosciute, oltre a quelle di `module-auth`, e come un progetto
  ne dichiara altre.
- Quanto in profondità va la checklist su better-auth.

## Scelte mie, da controllare

- Una skill nuova, `app-security`, come quinto controllo, invece di aggiungere sezioni a `compliance-audit` o a
  `vercel-deploy`.
- Il nome `app-security`, per non confondersi con il comando integrato `/security-review`.
- Non si appoggia a `cso`, `security-guidance` o `claude-security`: sono su questa macchina ma non fanno parte
  di dev-flow. La checklist cita `/security-review` come passaggio facoltativo sulla diff del branch.
- Strix come livello dinamico facoltativo, mai di default.
- Non installa strumenti da sola: propone il comando e chiede conferma.
- Come gli altri controlli, non blocca il deploy; i segreti trovati nella cronologia vanno ruotati, e il report lo
  dice in testa.
