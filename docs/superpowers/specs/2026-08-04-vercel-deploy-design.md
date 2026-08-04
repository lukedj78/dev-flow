# `vercel-deploy` — chiudere il riferimento dangling `setup-deploy` — 2026-08-04

`setup-deploy` era instradato dall'orchestratore ma **non è mai esistito**: `git log --diff-filter=D -- 'setup-deploy/*'` è vuoto, quindi non è il residuo di una cancellazione ma un nome aspirazionale rimasto in prosa per mesi. Questo documento decide cosa costruire al suo posto e perché il nome cambia.

## Il buco, in una riga

Per `stack.framework ∈ {next, monorepo}` la transizione `feature_complete` → `deployed` **non ha proprietario**. Mobile ce l'ha (`rn-eas-deploy`, che setta `phase = "deployed"`), agent ce l'ha (`eve deploy`), il web finisce in un vicolo cieco.

## Perché non basta ritargettare su `module-add deploy`

L'ipotesi naturale — «i riferimenti puntano al modulo che già configura Vercel» — è contraddetta dal modulo stesso:

- `module-add/references/module-deploy.md:200` — «Do **not** run `vercel deploy` from this module».
- `module-add/references/module-deploy.md:212` — «never bump toward `deployed` here; only `setup-deploy` earns that».

Ritargettare vorrebbe dire **riscrivere quel confine**, non documentarlo: nessuno spedirebbe, nessuno gestirebbe domini o rollback, e la fase `deployed` la chiuderebbe l'utente a mano. Il buco non si chiude, si ridefinisce.

## Perché il nome cambia in `vercel-deploy`

1. **Collisione reale.** `~/.claude/skills/setup-deploy` esiste già come symlink a `gstack/setup-deploy` (skill di terze parti). `install.sh` copia ogni skill in `$SKILLS_DIR/<name>`: una `setup-deploy` di dev-flow sovrascriverebbe quella di gstack (con backup `.bak`) e i due nomi sarebbero ambigui nel registry dell'agente.
2. **Simmetria.** La controparte mobile si chiama `rn-eas-deploy` — per la piattaforma, non per il verbo "setup".
3. **Verità del nome.** Il *setup* è già di `module-add deploy`. Questa skill **spedisce**.

## Confine di responsabilità

| Cosa | Owner |
|---|---|
| link progetto, `vercel.json`, regione, matrice env per ambiente, root directory monorepo | `module-add deploy` |
| husky, lint-staged, GitHub Actions | `module-add ci` |
| gate costo/perf (caching, durata funzioni, immagini, dead code) | `vercel-doctor` |
| gate legale (GDPR/AI-Act, residenza dati) | `compliance-audit` |
| **spedire**: preview → smoke → produzione staged → promote, domini + DNS, rollback, `phase = "deployed"` | **`vercel-deploy`** |

`vercel-deploy` non riscrive `vercel.json` e non tocca la matrice env: se mancano, instrada a `module-add deploy` e si ferma.

## I fatti dei docs che disegnano il workflow

Verificati il 2026-08-04 sui docs ufficiali Vercel. Non sono dettagli: cambiano la forma della skill.

1. **«The first deployment of a new project is always a production deployment, even when you run `vercel` without `--prod`.»** (`/docs/cli/deploying-from-cli`) → il passo "preview prima, produzione poi" **non esiste al primo deploy**. La skill deve biforcare, altrimenti promette un passo che il CLI non esegue.
2. **Staged production è il pattern sicuro**: `vercel --prod --skip-domain` crea un deployment di produzione che non serve traffico; `vercel promote <url>` lo rende **Current senza rebuild**. `--skip-domain` richiede `--prod` e sovrascrive l'impostazione di progetto *Auto-assign Custom Production Domains*.
3. **`vercel alias` non è la via giusta.** I docs stessi (`/docs/cli/alias`, sezione *Preferred production commands*) rimandano alla triade `--prod --skip-domain` → `promote` → `rollback`. `alias` resta per assegnazioni custom fuori dal Git flow.
4. **Dopo un rollback Vercel spegne l'auto-assign dei domini di produzione**: i push sul production branch non vanno più live finché non si esegue `vercel promote`. È la trappola operativa che va scritta esplicitamente.
5. **Il rollback non ricostruisce**: env vars e cron tornano allo stato del deployment ripristinato. Hobby può tornare solo al deployment di produzione immediatamente precedente.
6. **Domini**: il DNS vieta CNAME sull'apex, quindi Vercel raccomanda `www` come primario con redirect dall'apex. Apex = record **A**; subdomain = **CNAME** a un valore **unico per progetto** — mai hardcodato.
7. **Il percorso di default resta la Git integration**: push sul production branch (`main`, poi `master`, poi il default del repo) = deploy di produzione. Il CLI serve per staged/promote/rollback/domini, non per sostituire il git flow.
8. **`--prebuilt` perde le System Environment Variables in build** → sconsigliato per Next se il build le legge.

## Struttura

```
vercel-deploy/
  SKILL.md                    stile rn-eas-deploy: contratto, precondizioni, workflow, anti-pattern
  references/
    contracts.md              vendorizzato, byte-identico al canonico
    deploy-checklist.md       pre-flight: gate, build, env, primo-vs-successivo
    domains-dns.md            apex/www, A/CNAME, redirect, verifica, alias
    rollback-runbook.md       instant rollback, limiti di piano, trappola auto-assign, undo
```

### Workflow (11 step)

1. Precondizioni: `stack.framework ∈ {next, monorepo}` (se `expo-rn` → rifiuta, instrada a `rn-eas-deploy`); `phase ≥ feature_complete`; `.vercel/project.json` presente; `stack.deploy == "vercel"` — altrimenti `module-add deploy` prima.
2. Gate: leggi `meta.json#compliance` e `#vercel_doctor`, proponi se assenti o stantii. **Non blocca** — coerente con la policy esistente dei gate.
3. Build di verifica (`pnpm build`) + `vercel env ls`: la preview che va in 500 per una var mancante è il caso più comune.
4. Biforcazione primo deploy vs successivi.
5. Preview deploy + smoke guidato (solo percorso "successivi").
6. `vercel --prod --skip-domain` (staged).
7. Smoke sull'URL staged.
8. `vercel promote <url>` → Current.
9. Domini: add + DNS + redirect apex/www, idempotente.
10. Verifica post-deploy + consegna del runbook di rollback.
11. `meta.json`: `phase = "deployed"`, `stack.deploy = "vercel"`, `stack_config.production_url`, `history`. Commit.

### Anti-pattern da scrivere

- `vercel --prod` diretto su un progetto che ha già traffico (salta lo staged).
- `--prebuilt` su Next che legge System Env Vars in build.
- `phase = "deployed"` prima che il dominio di produzione serva davvero il deployment.
- Assumere che il rollback riporti anche le env vars.
- Lasciare il progetto in stato rolled-back senza dire che i push su main non vanno più live.
- Hardcodare il CNAME `*.vercel-dns-*.com`: è per progetto.

## Registrazione (stesso commit)

- `TAXONOMY` in `scripts/build_skills_registry.py`: `"vercel-deploy": ("web", "operative")` → web **13 → 14**, totale **41 → 42**.
- `install.sh` (array + commenti di conteggio) e `uninstall.sh`.
- `scripts/build_plugin_manifest.py` (la description dice "41 skills") → rigenerare `.claude-plugin/plugin.json` e `skills.json`.
- `README.md`: tabella web, conteggi, riga su `module-add deploy`, flusso monorepo.
- `CONTEXT.md`: i conteggi "41" (tre occorrenze).
- `docs/dev-flow-skill-map.html`, `docs/vercel-changelog-watch.md`, `CHANGELOG.md`.
- Rebuild `dist/` e `python3 scripts/lint_skills.py`.

### Retarget

`dev-flow/SKILL.md`, `dev-flow/references/stack-monorepo.md`, `dev-flow/references/stack-expo-rn.md`, `module-add/SKILL.md`, `module-add/references/module-deploy.md`, `vercel-doctor/SKILL.md`.

### Il contratto cambia

`dev-flow/references/contracts.md` (canonico) cita `setup-deploy` nella riga `feature_complete` della tabella delle fasi. Si aggiorna il canonico e si **ri-vendorizza byte-identico** in tutte le copie `*/references/contracts.md`.

## Guardrail: check #8 del linter

Il check #6 riconosce solo i riferimenti in forma `` `<name>/SKILL.md` `` — **è esattamente per questo che `setup-deploy` in backtick è sopravvissuto**. Il nuovo check #8 esamina i token kebab-case in backtick preceduti da un marcatore di routing (`→ \`x\``, `invoke \`x\``, `route to \`x\``, `that's \`x\``, `use \`x\``) e li verifica contro le skill esistenti più una allowlist esplicita di nomi esterni (pacchetti npm, CLI di terze parti). Ambito ristretto per tenere basso il rumore; un falso positivo si risolve aggiungendo una riga all'allowlist.

## Fuori scope

- Target di deploy alternativi (Fly.io, Cloudflare, Render): restano varianti da implementare su richiesta, come già dichiarato in `module-deploy.md`.
- Un workflow GitHub Actions che deploya: la Git integration *è* la CI di Vercel. `module-add ci` resta il proprietario di Actions.
