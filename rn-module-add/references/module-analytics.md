# rn-module-add → `analytics` (product · advanced)

The Expo side of `module-add/references/module-analytics.md`: the same opt-in rule, the same levels, the same
event names and the same `## Measurement` section in the PRD. Read that file's §Before anything first — targets
before code, written into the PRD when missing. What changes on mobile is where the events go.

| Level | On mobile |
|---|---|
| `traffic` | **Does not exist.** Installs and store-page views come from App Store Connect and Play Console, with no code. Say so and install nothing. |
| `product` | an `analytics_events` store in the app's backend, `track()` from the app, activation and D7/D30 from the backend |
| `advanced` | `posthog-react-native` (EU host), or `@openpanel/react-native` for `eu-sovereign` |

## Idempotency check

- `product`: `lib/analytics/track.ts` exists in the app (or `apps/mobile/` in a monorepo).
- `advanced`: `package.json` has `posthog-react-native` (or `@openpanel/react-native`).

A level already wired is reported, not reinstalled.

## Prerequisites

- `product` needs the backend and auth modules (`stack.db`, `stack.auth`): every event carries the signed-in
  user's id, which is what makes retention possible without a cookie or an advertising id.
- In a monorepo, the event catalogue lives in the shared package (`packages/shared/src/analytics/events.ts`), so
  web and mobile import the same names.

## `product`, per backend

The event catalogue is the web one, generated from the PRD:

```typescript
// lib/analytics/events.ts — or packages/shared/src/analytics/events.ts in a monorepo
export const EVENTS = ["signed_up", "invoice_sent", "client_added"] as const;
export type AnalyticsEvent = (typeof EVENTS)[number];
export const ACTIVATION_EVENT: AnalyticsEvent = "invoice_sent";
```

On mobile the user id comes from the session, so the signature is `track(event, props?)`. It never blocks the
UI and never throws; offline, events wait in AsyncStorage and are sent on the next call. Calls are flushed one
at a time, so concurrent events are neither duplicated nor lost (checked with a concurrency harness, 2026-10-18).

### Supabase

Table and policy (a migration in the Supabase project):

```sql
create table analytics_events (
  id bigserial primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  props jsonb,
  created_at timestamptz not null default now()
);
create index analytics_events_user_idx on analytics_events (user_id, created_at);
alter table analytics_events enable row level security;
create policy "insert own events" on analytics_events for insert to authenticated
  with check (user_id = auth.uid());
-- no select policy: the app writes events, it never reads other users' rows
```

`on delete cascade` makes the rows follow the account (DSAR deletion). The signup is recorded by the database
itself, so it cannot be missed by an app that crashed after sign-up:

```sql
create function analytics_signed_up() returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into analytics_events (user_id, name) values (new.id, 'signed_up');
  return new;
end $$;
create trigger analytics_signed_up after insert on auth.users
  for each row execute function analytics_signed_up();
```

`lib/analytics/track.ts`:

```typescript
import AsyncStorage from "@react-native-async-storage/async-storage";
import { supabase } from "@/lib/supabase";
import type { AnalyticsEvent } from "./events";

type Pending = { name: AnalyticsEvent; props: Record<string, unknown> | null; created_at: string };
const QUEUE = "analytics:pending";

async function pending(): Promise<Pending[]> {
  try {
    return JSON.parse((await AsyncStorage.getItem(QUEUE)) ?? "[]") as Pending[];
  } catch {
    return [];
  }
}

async function flush(next: Pending): Promise<void> {
  const { data } = await supabase.auth.getSession();
  const userId = data.session?.user.id;
  if (!userId) return;   // anonymous: not part of D7/D30
  const rows = [...(await pending()), next];
  const { error } = await supabase.from("analytics_events").insert(rows.map((r) => ({ ...r, user_id: userId })));
  await AsyncStorage.setItem(QUEUE, JSON.stringify(error ? rows.slice(-200) : []));
}

// One flush at a time: two concurrent calls would read the same queue, insert it twice, or one would empty
// it after the other had just added to it.
let chain: Promise<void> = Promise.resolve();

/** Record a product event for the signed-in user. Never throws; offline events wait in AsyncStorage. */
export function track(event: AnalyticsEvent, props?: Record<string, unknown>): Promise<void> {
  // created_at is the moment it happened on the device: an event sent later from the offline queue keeps it.
  const next: Pending = { name: event, props: props ?? null, created_at: new Date().toISOString() };
  chain = chain.then(() => flush(next)).catch(() => {});   // measurement must never break the screen
  return chain;
}
```

Activation and retention: the SQL in `module-add/assets/analytics/metrics.sql`, run in the Supabase SQL editor
with `:activation` replaced by the event name. The table has the same columns as the web one.

### Firebase

A Firestore collection `analytics_events`, written from the signed-in client. Security rule:

```
match /analytics_events/{id} {
  allow create: if request.auth != null
                && request.resource.data.user_id == request.auth.uid
                && request.resource.data.name is string;
  allow read, update, delete: if false;
}
```

`track()` is the Supabase version with `addDoc(collection(db, "analytics_events"), { user_id, name, props,
created_at: serverTimestamp() })` in place of the insert. Call `track("signed_up")` right after
`createUserWithEmailAndPassword` resolves (or from an auth `onCreate` Cloud Function, which does not depend on
the app staying open). Firestore does not run SQL, so activation and
retention come from a Node script with the Admin SDK (`firebase-admin`): read the events of the last 60 days,
group by user, take each user's first event as the signup, and apply the definitions in `metrics.sql`'s header.

**Not Google Analytics for Firebase**, even though it computes retention: it is Google Analytics — the service
the Italian Garante sanctioned — and the data does not stay in the EU.

### Custom REST · tRPC

The events go to the backend's own database: `track()` calls `POST /events` (or a tRPC `analytics.track`
procedure) with `{ name, props }`, and the backend records them with the signed-in user from the request. If
that backend is the Next app of a monorepo, it is exactly the web module's `product` level: the procedure calls
its `track(session.user.id, name, props)`, and `signed_up` comes from the backend's own auth hook.

## `advanced`

```bash
npx expo install posthog-react-native expo-file-system expo-application expo-device expo-localization
```

```tsx
import { PostHogProvider } from "posthog-react-native";

<PostHogProvider apiKey={process.env.EXPO_PUBLIC_POSTHOG_KEY!} options={{ host: "https://eu.i.posthog.com" }}>
  {children}
</PostHogProvider>
```

Start opted out (`defaultOptIn: false` in `options`) and call `posthog.optIn()` then `identify()` only after the
user consents in the app. PostHog does not use the advertising identifier, so no
App Tracking Transparency prompt is needed. For `eu-sovereign`: `@openpanel/react-native`, pointed at the
self-hosted instance. Register the provider: `dev-flow/scripts/data_residency.py add … --by rn-module-add`.

> **Checked 2026-10-18** with `npm view`: `posthog-react-native` 4.81.2, `@openpanel/react-native` 1.4.1,
> `@react-native-async-storage/async-storage` 3.1.1 (take the version `npx expo install` picks — the SDK pins it).

## The store listings

With `product` or `advanced` the app collects usage data, and the stores ask for it: the **App Store privacy
label** (Data Used to Track You: no; Data Linked to You: usage data, user id) and Google Play's **Data safety**
section. Tell the user before the next submission (`rn-publishing-payments/references/review-guidelines.md`).

## Update meta.json

The same keys as the web: add the level to `stack.analytics`, never remove one; `analytics_provider` with
`advanced`. In a monorepo the list is shared: `traffic` belongs to the web app, `product` to both.

## Known caveats

- **No `traffic` level on mobile** — the store consoles are the traffic report.
- **Retention counts signed-in users only.** Before sign-in there is no stable id, and the app does not invent one.
- **The offline queue is capped** at the last 200 events, so a phone offline for weeks does not grow without limit.
- **`created_at` is the device's clock**, so a queued event keeps the time it happened; a phone with a wrong clock
  skews its own rows, not anyone else's.
- **Before release**, the two measurement checks are in `rn-eas-deploy/references/deploy-checklist.md`
  (`launch-audit` does not run on mobile).
