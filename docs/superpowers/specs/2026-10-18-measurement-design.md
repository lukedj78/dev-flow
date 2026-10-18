# Misurazione — facoltativa, a livelli, attivabile quando serve — 2026-10-18

Primo punto della roadmap uscita dal confronto con *The Founder's Playbook*
(`2026-10-17-founder-intelligence-design.md`, §Confronto). Oggi dev-flow non misura niente dopo il lancio.
Peggio: `launch-audit` segnala «nessun analytics» e manda la correzione a `module-add`, che non ha un modulo
analytics. Il rimando va a vuoto.

Il PDF chiede di decidere le metriche **prima** del lancio: l'evento di attivazione, la retention a 7 e 30
giorni e cosa sarebbe un falso positivo (iscrizioni senza attivazione, ricavi senza retention). Chi sceglie le
metriche dopo, guardando i grafici, misura quello che sembra funzionare invece di quello che non funziona.

## Decisioni dell'utente (2026-10-18)

1. **La misurazione è facoltativa.** Un prototipo o uno strumento interno spesso non ne ha bisogno: si attiva
   solo se l'utente la chiede, e chi non la chiede non riceve né domande ripetute né segnalazioni.
2. **Si può attivare più tardi.** Un prototipo promosso a prodotto deve poterla aggiungere in qualsiasi
   momento, senza rifare niente.
3. **La suite resta quella di Vercel**, con un sistema misto che tenga conto della residenza dei dati in
   Europa e del fatto che Vercel Analytics non misura la retention.
4. **Anche React Native, in questo stesso lavoro**: le app Expo devono poter misurare come quelle web.

## Fatti verificati (2026-10-18)

Pacchetti verificati con `npm view`; comportamenti dalla documentazione ufficiale.

- **Vercel Web Analytics** (`@vercel/analytics` 2.0.1):
  - `<Analytics />` nel layout; dalla versione 2 non serve un proxy.
  - Niente cookie di terze parti: il visitatore è un hash della richiesta, scartato dopo 24 ore. Quindi
    **niente retention** su più giorni e niente funnel.
  - Eventi personalizzati, anche da server action (`track` da `@vercel/analytics/server`), **solo sul piano
    Pro**. Hobby: 50.000 eventi al mese.
  - Regione dei dati non verificata. Vercel è già un sotto-fornitore di ogni progetto deployato lì.
- **Retention a 7 e 30 giorni:** la fanno PostHog, OpenPanel e Umami Cloud. Non la fanno Vercel Web Analytics,
  Plausible e Aptabase.
- **La retention degli utenti autenticati non richiede un fornitore esterno.** Serve un identificativo stabile:
  per un utente con login c'è già, è il suo id. Con una tabella di eventi nel database del progetto, attivazione
  e retention diventano due query. I dati restano dove sta il database (Neon EU per un progetto `eu`), senza
  cookie e senza un sotto-fornitore nuovo.
- **PostHog** (`posthog-js` 1.438.12, `posthog-node` 5.56.2):
  - Cloud EU a Francoforte, DPA gratuito, 1 milione di eventi al mese gratis.
  - Società statunitense: non va bene per `eu-sovereign`.
  - Cookie per default; `cookieless_mode` disponibile.
  - `@posthog/next` è ancora pre-release e punta per default all'host US.
- **OpenPanel** (`@openpanel/nextjs` 1.5.1): europeo (Stoccolma, dati da Hetzner in Germania), cookieless, fa
  retention e funnel, self-hostabile. Il cloud usa Cloudflare (US) come rete di bordo.
- **Nel repo:**
  - `eu-data-sovereignty.md` §4.9 elenca già PostHog Cloud EU e Umami self-hosted come default, senza dire chi
    fa la retention.
  - `data_residency.py` (`IMPLIED`) non conosce nessun fornitore di analytics.
  - `compliance-audit` non si accorge se un analytics si carica prima del consenso.
  - Il PRD non ha una sezione per le metriche.

## Obiettivi

1. Chi vuole misurare decide le metriche prima di misurare, nel PRD.
2. Chi non vuole misurare non viene disturbato, né dalla skill né dai controlli prima del deploy.
3. Tre livelli indipendenti, ognuno attivabile da solo e in qualsiasi momento: traffico, prodotto, avanzato.
4. Il livello che conta per le metriche del PRD (prodotto) non aggiunge fornitori, non richiede cookie e tiene
   i dati nella regione del database.
5. `launch-audit` controlla le metriche solo dove sono state scelte.

## Non obiettivi

- Dashboard grafiche, data warehouse, feature flag, A/B test. Il livello avanzato apre PostHog, che li ha, ma
  il modulo non li collega.
- Analytics di marketing e attribuzione, Google Analytics (in Italia il Garante ne ha sanzionato l'uso).
- Osservabilità (errori, log, uptime): è il punto 4 della roadmap.

## Anti-obiettivi

- Chiedere metriche a chi sta facendo un prototipo e non le vuole.
- Un modulo che spara eventi ovunque e nessuno sa quale conta.
- Proporre Vercel Analytics o Plausible per la retention: non possono farla.
- Un analytics che si carica prima del consenso, in un progetto che dice di rispettarlo.

## Il design

### 1. I tre livelli

| Livello | Cosa misura | Con cosa | Fornitori nuovi | Prerequisiti |
|---|---|---|---|---|
| `traffic` | visite, pagine, provenienza, Web Vitals | Vercel Web Analytics + Speed Insights | nessuno (Vercel c'è già) | deploy su Vercel |
| `product` | evento di attivazione, retention D7/D30, eventi del PRD | una tabella di eventi nel database del progetto, `track()` lato server, query di attivazione e retention | nessuno | `stack.db` deciso; la sezione *Measurement* nel PRD |
| `advanced` | funnel con interfaccia, session replay, dashboard | PostHog Cloud EU, oppure OpenPanel per `eu-sovereign` | uno, registrato con `data_residency.py add` | richiesta esplicita |

I livelli si combinano. Il caso tipico è un prodotto con `traffic` e `product`; `advanced` si aggiunge quando
servono le dashboard. Su Vercel Hobby `traffic` funziona; gli eventi personalizzati di Vercel (Pro) non
servono, perché le metriche del PRD le fa `product`.

### 2. Il contratto: `stack.analytics`

Nuova chiave in `contracts.md` §stack: la lista dei livelli attivi, per esempio `["traffic", "product"]`;
`[]` o assente vuol dire non richiesta. Con `advanced` si aggiunge `stack.analytics_provider`:
`"posthog" | "openpanel"`. Una riga nella tabella dei default consigliati. Aggiunta additiva:
`contract_version` resta 1, e la copia aggiornata va in tutte le skill che vendorizzano `contracts.md`.

`data_residency.py` aggiunge a `IMPLIED` `("analytics_provider", "posthog"): "PostHog"` e
`("analytics_provider", "openpanel"): "OpenPanel"`. `traffic` è coperto dalla riga Vercel, che c'è già;
`product` non aggiunge niente.

### 3. Come si attiva

- **All'inizio, percorso diretto:** `prd-from-idea` aggiunge una domanda breve: *«vuoi misurare l'uso del
  prodotto?»*. Se la risposta è no, non scrive niente e non chiede altro. Se è sì, chiede le metriche (§4).
- **All'inizio, percorso Founder Intelligence:** le metriche sono già nel Playbook §12 che il founder ha
  approvato, quindi la sezione *Measurement* si riempie da lì.
- **Più tardi:** in qualsiasi fase, una richiesta come *«adesso voglio misurare l'uso»* o *«aggiungi gli
  analytics»* va a `module-add analytics`. Se il PRD non ha *Measurement*, il modulo chiede le metriche, le
  scrive nel PRD (una revisione, non un PRD nuovo) e poi collega i livelli. Un livello già attivo si salta; uno
  nuovo si aggiunge senza toccare gli altri.
- **Esecuzione autonoma:** senza una richiesta esplicita, niente misurazione.

### 4. La sezione *Measurement* nel PRD

Solo nei progetti che misurano, dopo *User stories*:

```markdown
## Measurement

Decided before launch, not after. Levels: traffic, product.

- **Activation event**: `<event_name>` — <what the user has done when they first get the value>
- **Retention targets**: D7 ≥ <n> % · D30 ≥ <n> % of activated users
- **False positives to watch**: <e.g. sign-ups without activation; revenue without retention>
- **Events to instrument**: `<event_name>` (where it fires) · …
```

I nomi degli eventi sono in `snake_case`, verbo al passato (`invoice_sent`): stabili, perché sono le chiavi del
modulo e dei controlli. Le risposte che l'utente non sa dare diventano `<TBD — needs user input>`, come in tutto
il PRD. Con solo `traffic` basta la riga dei livelli: il traffico non ha obiettivi da scrivere.

### 5. Il modulo `module-add analytics`

`module-add/references/module-analytics.md`, nello schema degli altri moduli (verifica di idempotenza,
prerequisiti, installazione, file da scrivere, variabili d'ambiente, verifica, `meta.json`, avvertenze), con
una parte per livello.

- **`traffic`:** `<Analytics />` e `<SpeedInsights />` nel layout; niente invio da preview e sviluppo
  (`VERCEL_ENV`, come dice già `module-deploy`).
- **`product`:**
  - Una tabella `analytics_events` (id, `user_id`, `name`, `props` JSON, `created_at`) nello schema del
    database del progetto, con la migrazione dello stack (Drizzle su Neon).
  - `lib/analytics/events.ts`: il catalogo dei nomi, generato dalla lista del PRD, come tipo unione, così un
    nome sbagliato non compila.
  - `lib/analytics/track.ts`: `track(userId, event, props)` per le server action. Scrive una riga e non blocca
    mai la richiesta se fallisce.
  - `lib/analytics/metrics.ts`: le query di attivazione e di retention D7/D30 per coorte di iscrizione, e uno
    script (`npm run metrics`) che le stampa. Una pagina admin è lasciata al progetto.
  - Retention e dati personali: le righe sono legate all'id dell'utente, quindi seguono le regole di
    cancellazione dell'account, che `compliance-audit` controlla già (DSAR).
- **`advanced`:**
  - PostHog: `posthog-js` in `instrumentation-client.ts` con l'host EU scritto esplicitamente (mai il default US
    di `@posthog/next`), cookieless per il traffico anonimo, `identify()` solo dopo il consenso attraverso il
    gate `lib/consent.ts` di `compliance-audit`; proxy inverso con le rewrite di Next su un percorso neutro;
    `posthog-node` lato server.
  - OpenPanel per `eu-sovereign`, self-hosted; il cloud solo se l'utente accetta Cloudflare all'edge, registrato
    come trasferimento.
  - `track()` di `product` può inoltrare lo stesso evento anche al fornitore, così i nomi restano uno solo.
  - Il passo 1b di `module-add` sulla residenza, con `data_residency.py add`.
- **Stato:** aggiorna `stack.analytics` (e `analytics_provider` con `advanced`); la fase segue le regole già
  esistenti di `module-add`.
- La tabella dei moduli in `module-add/SKILL.md`, il catalogo del README e i conteggi si aggiornano.
- `eu-data-sovereignty.md` §4.9 aggiunge una colonna *retention D7/D30*, Vercel Web Analytics (traffico) e
  OpenPanel.

### 6. `launch-audit`

Tutti i controlli di misurazione si applicano **solo se il progetto ha scelto di misurare**, cioè se
`stack.analytics` non è vuoto. Altrimenti il report dice «misurazione non richiesta» e non lo conta come una
mancanza.

- **`analytics-absent`** (esiste già): riconosce anche `@openpanel/` e la tabella di `product`; manda a
  `module-add analytics`. In un progetto che non misura diventa «non richiesta».
- **Nuovo `measurement-targets`:** con `product`, il PRD deve avere *Measurement* con un evento di attivazione e
  obiettivi D7/D30 senza `TBD`; altrimenti lo segnala e manda a `prd-from-idea`.
- **Nuovo `activation-instrumented`:** se il PRD nomina l'evento di attivazione, lo cerca in una chiamata a
  `track` nel codice; se non c'è, lo segnala e manda a `module-add analytics`.
- Come sempre in `launch-audit`: niente punteggio, niente blocco; il motivo per ignorare un controllo va in
  `dismissed`.

### 7. `compliance-audit`

Il segnale già scritto nella checklist di R2 («un analytics scrive cookie prima del consenso») diventa un
controllo dello scanner: segnala un SDK client di analytics inizializzato senza modalità cookieless e senza il
gate del consenso. Riguarda il livello `advanced`; `traffic` (Vercel, senza cookie) e `product` (lato server) non
lo fanno scattare. È euristico, come gli altri controlli dello scanner, e lo dice.

### 8. React Native: `rn-module-add analytics`

Le app Expo hanno una famiglia di skill propria: i moduli si aggiungono con `rn-module-add`, e il backend è
uno dei quattro che quella skill supporta (Supabase, Firebase, Custom REST, tRPC). Stessi livelli, stessi nomi di
eventi, stessa sezione *Measurement* nel PRD; cambia il collegamento.

- **`traffic`:** su mobile non esiste. Le installazioni e le visite alla scheda le danno App Store Connect e
  Play Console, senza codice; il modulo lo dice e non installa niente.
- **`product`**, per backend:

| Backend | Dove vanno gli eventi | Come si scrivono | Attivazione e retention |
|---|---|---|---|
| Supabase | tabella `analytics_events` in Postgres | inserimento dal client autenticato, con una policy RLS che accetta solo `user_id = auth.uid()` | le stesse query SQL del web |
| Firebase | collezione Firestore `analytics_events` | dal client autenticato, con una regola di sicurezza che accetta solo il proprio `uid` | uno script Node con l'Admin SDK, perché Firestore non fa SQL |
| Custom REST · tRPC | il database del backend | `POST /events`, o una procedura tRPC, che chiama il `track()` del backend | sul backend; se il backend è l'app Next di un monorepo, è il livello `product` del web |

  `lib/analytics/events.ts` ha lo stesso catalogo dei nomi del web; in un monorepo vive nel pacchetto condiviso,
  così web e mobile non possono divergere. `track()` non blocca mai l'interfaccia e, senza rete, mette gli eventi
  in coda e li reinvia.
  Su Firebase si usa Firestore e non Google Analytics for Firebase, che pure fa la retention: è Google Analytics,
  lo stesso fornitore sanzionato dal Garante, e non resta in EU.
- **`advanced`:** `posthog-react-native` (4.81.2) con l'host EU scritto esplicitamente e `npx expo install`;
  `identify()` dopo il consenso dato nell'app. PostHog non usa l'identificativo pubblicitario, quindi non serve
  il prompt ATT di iOS. OpenPanel ha `@openpanel/react-native` per `eu-sovereign`.
- **Le schede degli store:** con `product` o `advanced` l'app raccoglie dati di utilizzo, e va dichiarato nella
  privacy label dell'App Store e nella sezione *Data safety* di Google Play. Il modulo lo ricorda, e la checklist
  di `rn-publishing-payments/references/review-guidelines.md` riceve una riga.
- **Prima del rilascio:** `launch-audit` rifiuta il mobile, quindi i due controlli (obiettivi nel PRD, evento di
  attivazione nel codice) diventano due righe nella checklist di `rn-eas-deploy`, valide solo se il progetto
  misura.
- La riga `analytics` nella tabella dei moduli di `rn-module-add` e in `module-matrix.md`; `stack.analytics` è la
  stessa chiave del web.

### 9. Founder Intelligence

Lo stadio 9 scrive già le metriche nel Playbook §12. `prd-from-idea` le porta nella sezione *Measurement*, e
`stack.analytics` parte con `["traffic", "product"]`, perché il founder ha già scelto di misurare. Una riga in
`stages.md` usa lo stesso formato e la stessa regola sui nomi degli eventi.

## Test

- `data_residency.py`: le due voci `IMPLIED` (un fornitore `advanced` dichiarato e non registrato viene
  segnalato).
- `launch-audit`:
  - progetto che non misura → «non richiesta», nessuna mancanza;
  - `measurement-targets`: assente, con `TBD`, completo;
  - `activation-instrumented`: evento nel codice, assente, PRD senza evento;
  - `analytics-absent` con la tabella di `product` e con OpenPanel.
- `compliance-audit`: SDK client con cookie e senza gate (segnalato), cookieless (non segnalato), con il gate
  (non segnalato), solo `@vercel/analytics` (non segnalato).
- Le query di retention: un test con una manciata di righe a date note, che controlla attivazione, D7 e D30 per
  coorte. Le query vivono nel riferimento del modulo come codice da copiare, quindi il test gira su una copia
  delle query con SQLite in memoria, se la sintassi lo permette; altrimenti la verifica è manuale su un'app di
  prova, e lo si dichiara.
- Una verifica a mano su un'app Next di prova con il modulo applicato e `npm run build`.
- React Native: il catalogo e `track()` per Supabase controllati con `tsc` sull'app Expo SDK 58 di prova; le regole RLS e Firestore come codice da copiare, verificate a mano se c'è un progetto di test, altrimenti dichiarate non eseguite.
- Tutte le suite, il lint, i bundle.

## Lasciato a chi costruisce

- La forma esatta della tabella, del catalogo e degli helper.
- Le soglie di esempio per D7/D30 quando l'utente le chiede, indicative e marcate come tali.
- Come lo scanner di `compliance-audit` riconosce il gate del consenso.

## Scelte mie, da controllare

- `stack.analytics` come lista dei livelli attivi, più `analytics_provider` solo per `advanced`.
- La retention calcolata dal database del progetto invece che da un fornitore; quindi `product` richiede un
  database.
- La domanda in `prd-from-idea` è una sola, e il no chiude l'argomento.
- Il modulo, invocato più tardi, scrive lui stesso la sezione *Measurement* nel PRD prima di collegare i livelli.
- PostHog come fornitore di `advanced`, OpenPanel per `eu-sovereign`.
- Su mobile niente livello `traffic`: le installazioni le danno App Store Connect e Play Console.
- Su Firebase il livello `product` usa Firestore e uno script Node, non Google Analytics for Firebase.
- Il controllo prima del rilascio mobile va nella checklist di `rn-eas-deploy`, perché `launch-audit` rifiuta il mobile.
