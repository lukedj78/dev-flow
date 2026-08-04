# vercel-deploy → custom domains and DNS

Attaching a real domain to the project, and getting the apex/`www` pair right the first time.

> **Versions checked 2026-08-04**: Vercel CLI `58.5.1`. Docs: <https://vercel.com/docs/domains/working-with-domains/add-a-domain>, <https://vercel.com/docs/domains/working-with-domains/deploying-and-redirecting>, <https://vercel.com/docs/cli/domains>, <https://vercel.com/docs/cli/alias>.

## The one rule that decides the shape

**The DNS spec forbids CNAME records on an apex domain** (`example.com`); they are allowed on subdomains (`www.example.com`). Everything below follows from that.

Vercel's recommendation: **use `www` as the primary domain, with a redirect from the non-`www` apex to it.** A CNAME lets Vercel steer traffic at the DNS level — during a DDoS, or for performance — where an A record hardcodes an IP. The redirect is also cached in the visitor's browser, so the second visit skips it.

Apex-primary is fully supported, not a downgrade: Vercel serves apex domains over Anycast. It simply gives the CDN less room to move traffic. Present the recommendation, then implement what the user chooses. Most browsers hide the `www` prefix in the address bar anyway, so the aesthetic objection is mostly moot.

## Records

| What | Record type | Value |
|---|---|---|
| apex (`example.com`) | **A** | the IP Vercel shows for your project |
| subdomain (`www`, `app`, `docs`) | **CNAME** | a **project-specific** target, e.g. `d1d4fc829fe7bc7c.vercel-dns-017.com` |
| domain already in use by another Vercel account | **TXT** | the verification value Vercel shows |

**Never hardcode either value.** The A record IP and especially the CNAME target are per project — the example above is from Vercel's own docs and is wrong for every real project. Read them from the dashboard or from `vercel domains verify --format=json`, then hand them to the user.

Alternative to individual records: point the registrar at **Vercel Nameservers**. Required for wildcard domains (`*.example.com`). Warning worth repeating to the user before they switch: moving nameservers means **every DNS record they want to keep must be re-created in Vercel** — MX for email above all. A team that loses its mail because it moved nameservers for a website launch will remember it.

## Commands

```bash
# add the domain to the project
pnpm dlx vercel@latest domains add <domain> <project>

# what records are expected vs what DNS currently answers
pnpm dlx vercel@latest domains verify <domain> --project <project> --format=json

# check only the exact domain, without falling back to the parent zone
pnpm dlx vercel@latest domains verify <domain> --strict

# inventory
pnpm dlx vercel@latest domains ls
pnpm dlx vercel@latest domains inspect <domain>
```

`--force` on `domains add` moves the domain off whichever project currently holds it. Do not reach for it to clear an error you have not read — that error usually means the domain is live on another project.

The registrar side is the user's to do. This skill reads the expected records and hands them over; it does not have registrar credentials and should not ask for them.

## Redirecting apex ↔ www

Add **both** domains to the project, then set the redirect in the dashboard: **Settings → Domains → Edit** on the domain you redirect *from*, and pick the target in the **Redirect to** dropdown.

Vercel attempts a `www`/non-`www` redirect automatically, but add it explicitly anyway — the automatic behaviour is a fallback, not a configuration.

Adding an apex domain prompts you to add its `www` counterpart. Take the prompt: having both means a visitor reaches the site whichever they type.

For route-level redirects (`/old` → `/new`) use `next.config.ts`, not the domain settings. Every `redirect`/`rewrite`/`header` entry also counts against the **2048 routes per deployment** limit.

## After the domain is configured

> *"Once the domain has been added to your project and configured, it is automatically applied to your latest production deployment."*

So: on a Git-connected project every push to the production branch reaches the domain from then on. If a domain is assigned to a **different branch**, a new deployment on that branch is required before it resolves.

## When `vercel alias` is still the right tool

Almost never, for production. The docs are explicit that the preferred production commands are `vercel --prod --skip-domain`, `vercel promote` and `vercel rollback`.

`vercel alias set <deployment-url> <custom-domain>` earns its place when you are **not** using the Git Integration and still need branch-based or heuristic domain assignment — e.g. pointing `staging.example.com` at a specific deployment from a custom CI. Custom domains with a configured preview branch are only applied by the Git Integration; outside it, `alias` is the manual equivalent.

Omit the protocol in the domain argument: `vercel alias set my-app-xyz.vercel.app app.example.com`, not `https://app.example.com`.

Two consequences to state when you use it: a custom alias is **not** part of the project's domain settings, so **a rollback does not restore it** unless it was present on the previous production deployment. And `vercel alias ls` is the only place it shows up.

## Limits

- Hobby: **50 custom domains per project**.
- Wildcard domains require the nameserver method.
- One TXT verification at a time when verifying access to a domain held by another account.
