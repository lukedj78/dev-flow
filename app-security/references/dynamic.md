# The dynamic level — Strix, on request only

The scan and the review read code. This level attacks the running app, and reports a problem only when an
exploit actually worked. It is worth its cost before a first public launch, or when the app holds
sensitive data or takes payments. It is never part of a default run.

[Strix](https://github.com/usestrix/strix) (`strix-agent` on PyPI, Apache-2.0) runs AI agents inside a
Docker sandbox. Flags and environment variables below were read from the published 1.7.0 wheel
(`strix/interface/cli_args.py`, `environment.py`) on 2026-10-18.

## 1. Authorization — first, and said out loud

Before anything is installed or started, tell the user, in these terms, and wait for a yes:

> Strix will attack **<the exact URL>**, which runs your app with test data. It sends real attack
> requests: it may create, change or delete data in that environment. I will not point it at production,
> at a domain or service that is not yours, or at a third-party API the app calls. Go ahead?

The rules behind that sentence, none of which a user's "just run it" overrides:

- **Only the user's own app**, running where they control it: `next start` on this machine, or a Vercel
  preview deployment of their project.
- **Never production with real data.** A preview connected to the production database counts as
  production: ask which database the target uses.
- **Never a third party.** If the app calls Stripe, Supabase or another API, those are not targets; say
  so in the instruction (step 4).
- One yes covers one run against one URL. A second target is a second question.

## 2. Prerequisites

- **Docker running** (`docker info` answers).
- **A model provider key, on the user's account.** Strix needs `STRIX_LLM` (the model name) and usually
  `LLM_API_KEY`. It does **not** use the Claude subscription; it can use a ChatGPT subscription through
  `strix auth login chatgpt`. The user exports the key in their own shell: never ask them to paste it
  here, never write it to a file.
- **Install with `pipx install strix-agent`**, after asking. Not the `curl | bash` script.

## 3. A test user, made for the run

A grey-box run finds what matters most here, IDOR between accounts. Create **two** test accounts in the
target environment (sign-up through the app, or the project's seed script), each owning at least one
object — a note, an order, a booking. Record the credentials in the project's seed or `.env.test` file,
not in chat.

## 4. Run

Put the instructions in a file, so the credentials stay out of shell history:

```text
# strix-instructions.txt (git-ignored; delete after the run)
Test only <URL>. Do not send requests to any other host.
Two test accounts: A = <email>/<password>, B = <email>/<password>.
Each owns objects. Try to read, change and delete A's objects while signed in as B, through
the pages, the Server Actions (POST with a Next-Action header) and the /api routes.
Focus on broken access control (IDOR), authentication, injection and data exposure.
```

```bash
strix -n --target http://localhost:3000 --instruction-file ./strix-instructions.txt \
      --scan-mode standard --max-budget-usd 10
```

- `-n` runs headless and exits at the end; with any finding it exits **2**, which is the result, not a
  crash.
- `--scan-mode` defaults to `deep`, the most expensive. Start with `standard`.
- `--max-budget-usd` stops the scan cleanly at that model spend. Agree the number with the user first.
- `--target` can also take a local directory, which Strix mounts **writable** into the sandbox. Do not
  point it at the repository: give it the URL.

## 5. Results

Strix writes to `./strix_runs/<run>/`: `penetration_test_report.md`, one file per finding under
`vulnerabilities/`, and `vulnerabilities.json`. Read each finding and its proof.

- Each proven finding enters the same report as the scan and the review, **marked "proven"**, and goes
  above every unproven one. Route it as in `SKILL.md` step 5.
- Record the run in `meta.json#security.dynamic`:

  ```json
  "dynamic": { "ran_at": "<ISO-8601 UTC>", "tool": "strix", "proven": 1 }
  ```

- `strix_runs/` holds the test credentials and working exploits. Add it to `.gitignore`, and delete the
  instructions file.
- A run with nothing proven is not a clean bill: it means these agents, in this budget, did not get in.

## 6. Cost

Every run spends model tokens on the user's provider key, at that provider's prices, plus the time of a
Docker sandbox on this machine. Say the budget before the run, and what it spent after. Strix tracks
tokens and an estimated cost per run; the provider's own usage page is the figure to trust.
