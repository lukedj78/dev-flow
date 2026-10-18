# Osservabilità — sapere che la produzione si è rotta prima che lo dica un utente — 2026-10-18

Quarto punto della roadmap (`2026-10-17-founder-intelligence-design.md:447`, verbatim):

> 4. **Osservabilità web** (M): un modulo in `module-add` per errori, log strutturati e uptime.

Il confronto con il Playbook lo segnava «presente solo per mobile, mancante per il web»
(`:426`), e il design della misurazione lo rimandava qui (`2026-10-18-measurement-design.md:67`).

## Fatti verificati (2026-10-18)

**Nel repo.**

- `error.tsx` è obbligatorio dallo scaffold (`design-md-to-app`), ma il template fa solo `console.error`, con un
  `TODO: replace console.error with structured logger when module-add observability lands`
  (`design-md-to-app/references/error.template.tsx:22-24`). L'errore che vede l'utente si perde nel suo browser.
- Non esistono `global-error.tsx`, `instrumentation.ts`, `onRequestError`, OpenTelemetry, log drain, uptime o
  allarmi. Un'eccezione di una Server Action finisce solo nei log runtime di Vercel, che su Hobby durano **un'ora**
  (`vercel-deploy/references/rollback-runbook.md:82`).
- La misurazione (`module-add analytics`, livello `traffic`) copre visite e Web Vitals con Speed Insights. Non copre
  gli errori.
- `module-email.md:274` dice «registra il caso `{ ok: false }` nel tuo monitoraggio», ma il monitoraggio non c'è.
- I fornitori sono già valutati per l'UE in `eu-data-sovereignty.md` §4.9:
  - errori: Sentry EU (Francoforte, da scegliere alla creazione dell'organizzazione); in alternativa GlitchTip o
    Bugsink, compatibili con l'SDK di Sentry;
  - log: Axiom (edge UE) e Better Stack (`germany`).
- Nel contratto non c'è nessuna chiave per l'osservabilità.
- **Mobile.** `rn-eas-deploy` dà per scontato Sentry o Bugsnag («Sentry / Bugsnag dashboard (if configured)»), ma
  nessuna skill lo installa (`rn-module-add` non ha crash reporting). EAS Observe misura le performance, non i
  crash.

**Fuori dal repo, dagli artefatti pubblicati.**

- `@sentry/nextjs` 11.8.0, MIT, con peer `next` `^14 || ^15 || ^16`.
- `next` 16.4.1, letto in Archi Studio, espone `onRequestError(error, request, context)` in `instrumentation.ts`
  (`next/dist/server/instrumentation/types.d.ts`).
- GlitchTip backend è MIT (GitLab, attivo il 2026-10-16). Il server di Sentry è sotto FSL 1.1, che non è una licenza
  OSI.
- Sentry ha la stessa tariffa in UE e in USA, e la regione UE è disponibile anche sul piano gratuito Developer
  ([data storage location](https://docs.sentry.io/changelog/data-storage-location-in-germany-is-generally-available/),
  [choose your data center](https://docs.sentry.io/product/accounts/choose-your-data-center/)).
- Vercel Observability Plus non ha più il costo base dal 2026-04-02: si paga per evento, con log di 30 giorni, solo
  sui piani Pro ed Enterprise ([changelog](https://vercel.com/changelog/no-base-fee-for-observability-plus.md)).

## Intento

Un modulo, `module-add observability`, che dà a un'app web tre cose, a livelli come la misurazione:

- **errori:** ogni eccezione, del client e del server, arriva a un tracker con la release che l'ha introdotta;
- **log:** righe strutturate che si possono collegare a una richiesta, e portate fuori da Vercel prima che spariscano;
- **uptime:** un controllo esterno che manda un avviso quando l'app non risponde.

In più, il pezzo mobile che oggi manca: `rn-module-add observability`, per il crash reporting di un'app Expo.

## Obiettivi

1. **Nessun errore in produzione resta invisibile.** `error.tsx`, `global-error.tsx`, `onRequestError` e il client
   lo inviano al tracker. Ogni evento porta la release (lo SHA del commit), così il rollback si decide sapendo quale
   deploy ha introdotto il problema.
2. **Rispetto della scelta UE già fatta nel progetto** (`stack.data_residency`):
   - `eu`: Sentry nella regione di Francoforte;
   - `eu-sovereign`: GlitchTip self-hosted, con lo stesso SDK e solo il DSN che cambia.

   Il fornitore entra nel registro dei sub-processor con `data_residency.py add`.
3. **Nessun dato personale per default:**
   - `sendDefaultPii: false`, e i corpi delle richieste non vengono inviati;
   - niente Session Replay;
   - `beforeSend` pulisce email e token dagli eventi.

   `compliance-audit` vede il tracker come sub-processor.
4. **Un log strutturato minimo** (`lib/log.ts`): JSON su stdout, con `requestId`, livello ed evento. I casi che
   oggi spariscono (`{ ok: false }` delle email, errori di `track()`, cron) lo usano. Un log drain verso Axiom o
   Better Stack è un'opzione, perché richiede il piano Pro di Vercel.
5. **Un controllo di salute e uptime:** una rotta `/api/health` (l'app risponde e il database risponde), e un
   monitor esterno che la chiama e manda un'email quando fallisce.
6. **Mobile:** `@sentry/react-native` con il plugin di Expo, mappe sorgente via EAS, regione UE. `rn-eas-deploy`
   rimanda al modulo invece di darlo per scontato.

## Non obiettivi

- APM e tracing distribuito completo (OpenTelemetry su tutto): si potrà aggiungere dopo, perché `@vercel/otel` si
  affianca senza cambiare niente.
- Dashboard, SLO, on-call e rotazioni.
- Session Replay: per scelta, per la privacy.
- Sostituire Speed Insights per i Web Vitals: resta quello della misurazione.

## Anti-obiettivi

- Un tracker che riceve email, token o corpi delle richieste.
- Un modulo che dà per riuscita la configurazione senza aver visto arrivare un evento vero.
- Allarmi per ogni rumore: il default avvisa solo sui problemi nuovi e sul down.
- Un fornitore fuori UE in un progetto che ha scelto `eu` o `eu-sovereign`.

## Il design

### 1. I livelli, come per la misurazione

`stack.observability` è un elenco dei livelli attivi, `["errors"]`, `["errors", "logs"]` o
`["errors", "logs", "uptime"]`. `stack.observability_provider` registra i fornitori:

```json
{ "errors": "sentry | glitchtip", "logs": "axiom | betterstack | none", "uptime": "sentry | betterstack" }
```

Un progetto può attivare un livello alla volta, in qualsiasi fase.

### 2. Il livello `errors` (`module-add/references/module-observability.md`)

- **File creati:**
  - `instrumentation.ts`, con `onRequestError = Sentry.captureRequestError` e l'inizializzazione per Node ed Edge;
  - `instrumentation-client.ts`, per il client;
  - `app/global-error.tsx`, che manca oggi.

  Il template di `error.tsx` passa da `console.error` a `Sentry.captureException`, e il `TODO` si chiude.
- **Release:** `release: process.env.VERCEL_GIT_COMMIT_SHA` e `environment: process.env.VERCEL_ENV`. Le mappe
  sorgente si caricano al build con `SENTRY_AUTH_TOKEN`, e la variabile la gestisce `project-infra-setup`, non la
  chat.
- **Privacy:**
  - `sendDefaultPii: false`;
  - `beforeSend` toglie i valori dei campi email e password, gli header di autorizzazione e i token dagli URL;
  - nessuna integrazione di Replay.
- **Regione:** il DSN deve essere `*.ingest.de.sentry.io` quando `stack.data_residency` vale `eu` o
  `eu-sovereign`, oppure l'host di GlitchTip. Un controllo lo verifica (§6).

### 3. Il livello `logs`

- **`lib/log.ts`:** `log.info/warn/error(event, fields)` scrive una riga JSON su stdout, con `ts`, `level`,
  `event`, `requestId` e i campi senza segreti. Il `requestId` viene da un header impostato in `proxy.ts`
  (`x-request-id`) e finisce anche nel tag dell'evento di Sentry, così un report dell'utente porta alla riga di log.
- **Drain:** su Pro, il drain di Vercel verso Axiom (dataset UE) o Better Stack (`germany`) si configura con
  `project-infra-setup`. Su Hobby i log restano un'ora, e il modulo lo dice chiaramente invece di nasconderlo.

### 4. Il livello `uptime`

- **`app/api/health/route.ts`:** risponde 200 con `{ ok, db, release }`, e 503 se il database non risponde.
  Nessun dato personale.
- **Il monitor esterno:** Sentry Uptime (stesso fornitore) o Better Stack, ogni minuto, con un'email all'indirizzo
  del progetto. Il modulo dà il comando o i passi, e non crea account.

### 5. Mobile: `rn-module-add observability`

- `@sentry/react-native` con il plugin di Expo e l'upload delle mappe sorgente nei build EAS;
- la stessa regola sulla regione e la stessa privacy del web;
- `ObserveErrorBoundary` di Expo 58 resta per EAS Observe, cioè per le performance.

`rn-eas-deploy` rimanda al modulo dove oggi scrive «if configured».

### 6. Il controllo (`module-add/scripts/observability_check.py`)

Uno script stdlib che legge il progetto e risponde, per ogni livello attivo:

| Livello | Cosa controlla |
|---|---|
| `errors` | `instrumentation.ts` con `onRequestError`; `instrumentation-client.ts`; `global-error.tsx`; `error.tsx` che invia l'errore; `release` impostata; `sendDefaultPii` non attivo; nessuna Replay; l'host del DSN coerente con `stack.data_residency` |
| `logs` | `lib/log.ts` e il `requestId` |
| `uptime` | la rotta `/api/health` |

Lo usano:
- **il modulo**, alla fine dell'installazione;
- **`vercel-deploy`**, al passo 2, che propone il modulo quando `stack.observability` è vuoto, senza bloccare;
- **`show_state`**, con una nota per un'app oltre `feature_complete` senza errori tracciati.

### 7. La prova, senza account

Un tracker vero richiede un account dell'utente, che il modulo non crea. Per provare che gli eventi partono
davvero, il modulo usa un **ricevitore locale**: un piccolo server stdlib che finge di essere Sentry
(`scripts/fake_ingest.py`) e annota le buste ricevute, con un DSN come `http://key@localhost:9010/1`.

L'app si avvia in locale, si provoca un errore in una Server Action e in un componente client, e si controlla che
il ricevitore abbia due eventi, con la release e senza dati personali.

Poi, con l'account dell'utente, basta cambiare il DSN. È la stessa disciplina di `app-verification`: niente «fatto»
senza un evento visto arrivare.

### 8. Dove entra nel flusso

- **dev-flow** lo propone una volta, prima del primo deploy in produzione (a `feature_complete`), e lo ripropone a
  ogni deploy finché manca. Non blocca mai.
- **`vercel-deploy`, passo 2:** legge `stack.observability` e il controllo.
- **`compliance-audit`:** il tracker e il drain sono sub-processor; li legge dal registro.
- **`launch-audit`:** non cambia, perché l'osservabilità non è prontezza commerciale.
- **Contratto:** le chiavi `stack.observability` e `stack.observability_provider`.

## Test

- **`observability_check.py`**, su fixture:
  - ogni elemento mancante viene segnalato, e un progetto completo passa;
  - un DSN USA in un progetto `eu` viene segnalato;
  - `sendDefaultPii: true` o un'integrazione di Replay vengono segnalati.
- **`fake_ingest.py`:** riceve una busta di Sentry e la annota.
- **`show_state`:** la nota.
- **Una prova vera** su Archi Studio (la cui cartella cambia spesso, quindi in un worktree) oppure su fit-coach:
  - il modulo applicato in una copia;
  - l'app avviata;
  - due errori provocati;
  - gli eventi visti nel ricevitore locale.

  Niente committato nei progetti.
- Il lint e tutte le suite.

## Lasciato a chi costruisce

- Il formato esatto del logger e la lista precisa dei campi tolti da `beforeSend`.
- Se usare il `tunnelRoute` di Sentry, che evita i blocchi degli adblocker ma passa dal server.

## Scelte mie, da controllare

- Un modulo dentro `module-add`, come chiede la roadmap, con un livello alla volta come la misurazione.
- **Sentry EU come default, GlitchTip per `eu-sovereign`:** stesso SDK, quindi passare dall'uno all'altro costa un
  DSN.
- Il pezzo mobile nello stesso lavoro, perché oggi è dato per scontato senza che nessuno lo installi.
- **Nessun gate:** è proposto prima del deploy e a ogni deploy finché manca.
- **La prova con un ricevitore locale finto**, perché non creo account a nome tuo.
