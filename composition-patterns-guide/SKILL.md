---
name: composition-patterns-guide
description: 'Use when refactoring React or React Native components that suffer from boolean prop proliferation, lack of compound structure, prop drilling, or unclear ownership of state. Codifies the 7 Vercel composition-patterns rules adapted to our web + RN stack: avoid boolean props (use composition or explicit variants), prefer compound components with shared context, lift state into providers, use children over render props, modern React 19 patterns (no forwardRef). Also enforces our colocation rules (Rule of Three for promotion, L0/L1/L2 hierarchy, _components/ naming). Triggers on: "refactor this component", "questo componente ha troppi prop booleani", "rendi questo componente più componibile", "compound component", "context provider per X", "design del componente". Not for: scaffolding new components from scratch (use design-md-to-app, screenshot-to-page, rn-add-screen), or moving components up the hierarchy (use promote-component).'
---

# composition-patterns-guide — modern React composition + our colocation rules

This skill is a **knowledge guardrail** that activates whenever you're designing, refactoring, or reviewing the architecture of a React/RN component. It combines two layers:

1. **The 7 Vercel `composition-patterns` rules** (originally from `vercel-labs/agent-skills`), adapted to our stack.
2. **Our colocation rules** (Rule of Three for promotion, L0/L1/L2, `_components/` and `components/shared/<dominio>/`).

It does NOT execute refactors — for that, use `promote-component`. It provides the *thinking framework*.

## When this skill applies

- About to add a 4th boolean prop to an existing component.
- About to write a component with `renderHeader`, `renderFooter`, `renderActions` render-prop callbacks.
- A component grew over ~250 lines and needs structural refactor.
- You see prop drilling 3+ levels deep.
- About to use `forwardRef` in new code (React 19+ projects).
- Reviewing a PR that touches component architecture.

Orchestrator does NOT route here automatically — invoked by the agent's own judgment when the patterns match.

## The 7 composition rules (priority order)

### Priority 1 — Component Architecture (HIGH)

#### Rule 1: Avoid boolean prop proliferation

**Wrong**:
```tsx
<Composer
  onSubmit={...}
  isThread={true}
  channelId={42}
  isDMThread={false}
  dmId={null}
  isEditing={true}
  isForwarding={false}
/>
```

Each boolean doubles the state-space. 5 booleans = 32 possible combinations, most of which are invalid or untested.

**Right** (composition):
```tsx
<Composer>
  <Composer.Header />
  <Composer.Input />
  <Composer.ThreadField channelId={42} />
  <Composer.EditActions />
  <Composer.Footer onSubmit={...} />
</Composer>
```

The consumer composes the parts they need. No invalid states.

#### Rule 2: Use compound components

A complex component should expose **subcomponents** that share context, not a single API with N props.

**Wrong**:
```tsx
function Card({ title, body, footer, showAvatar, avatarUrl }) {
  return <div>...</div>;
}
```

**Right**:
```tsx
function Card({ children }) {
  return <div className="card">{children}</div>;
}
function CardHeader({ children }) { return <div className="card-header">{children}</div>; }
function CardBody({ children }) { return <div className="card-body">{children}</div>; }
Card.Header = CardHeader;
Card.Body = CardBody;
// usage:
<Card>
  <Card.Header><Avatar src="..." /><h2>Title</h2></Card.Header>
  <Card.Body>...</Card.Body>
</Card>
```

If the subcomponents share state (e.g., a Disclosure that opens/closes), wrap in a context provider.

### Priority 2 — State Management (MEDIUM)

#### Rule 3: Decouple state from implementation

A provider should expose `{ state, actions, meta }` — a generic interface — not surface every state variable as a separate prop.

**Wrong**:
```tsx
<DialogProvider isOpen={isOpen} setIsOpen={setIsOpen} title={title} setTitle={setTitle}>
```

**Right**:
```tsx
<DialogProvider value={dialogStore}>  {/* zustand/jotai/use-state hook returns {state, actions, meta} */}
```

Then consumers use `useDialog()` and get the same interface regardless of how the state is stored.

#### Rule 4: Lift state into provider components

When siblings need to share state, move it into a provider that wraps both. Don't drill props through their parent.

#### Rule 5: Context interface — `{state, actions, meta}` shape

The provider's context value follows a predictable shape:
```ts
type CardContext = {
  state: { isExpanded: boolean };
  actions: { toggle: () => void };
  meta: { id: string };
};
```

This makes contexts mockable in tests (`mockContext({state: {...}, actions: {...}})`) and substitutable in Storybook.

### Priority 3 — Implementation Patterns (MEDIUM)

#### Rule 6: Children over render props

**Wrong**:
```tsx
<DataTable renderHeader={() => <Header />} renderRow={(row) => <Row data={row} />} />
```

**Right**:
```tsx
<DataTable>
  <DataTable.Header />
  {rows.map(r => <DataTable.Row key={r.id} data={r} />)}
</DataTable>
```

JSX as children is more readable, more compose-able, and supports tooling (highlighting, refactor, ref forwarding) better than render props.

#### Rule 7: Explicit variants (sometimes)

For variants that change visual identity significantly, create explicit named exports:

```tsx
// Instead of:
<Button variant="primary" size="lg">Save</Button>
<Button variant="ghost" size="sm">Cancel</Button>

// Consider:
<PrimaryButton>Save</PrimaryButton>
<GhostButton size="sm">Cancel</GhostButton>
```

⚠️ Caveat: shadcn / Radix use `variant` props heavily (via `cva`) and that's idiomatic in those libraries. The "explicit variants" rule applies more to *application-level* components than primitives.

### Priority 4 — React 19 APIs (MEDIUM, only React 19+)

#### Rule 8: No forwardRef

In React 19, `ref` is a normal prop. Don't use `forwardRef` for new code.

**Wrong**:
```tsx
const Button = forwardRef<HTMLButtonElement, Props>((props, ref) => (
  <button ref={ref} {...props} />
));
```

**Right**:
```tsx
function Button({ ref, ...props }: Props & { ref?: Ref<HTMLButtonElement> }) {
  return <button ref={ref} {...props} />;
}
```

Same for `use()` instead of `useContext()`:
```tsx
const ctx = use(MyContext); // React 19+, supports conditional reads
```

## Server/Client Component boundary (App Router)

Composition decisions above interact with the Server/Client split — get this wrong and a compound component either forces the whole tree client-side or fails to render at all:

- **A compound's root/provider is a Client Component the moment it needs `useState`/context for shared state** (Rule 4/5) — mark it `"use client"`. That does **not** force its subcomponents client-side too: a Server Component can still be passed as `children` into a Client Component's slot (e.g., `<ClientProvider>{await ServerFetchedContent()}</ClientProvider>` composed from a parent Server Component) — React keeps the Server-rendered subtree server-rendered even though the wrapping provider is a Client Component.
- **Don't add `"use client"` to a compound component just because one subcomponent needs interactivity.** Push the directive down to the smallest leaf that actually needs it (the button, the toggle), not up to the compound root — this preserves rung-1 colocation and avoids client-bundling the whole component for one `onClick`.
- **`children`-over-render-props (Rule 6) is also the standard way to keep a Server Component inside a Client Component's layout**: the Client Component (e.g., a `<Tabs>` shell needing `useState` for the active tab) renders `{children}` it received from a Server Component parent, rather than importing and rendering Server-fetched content itself (a Client Component cannot `import` and render a Server Component directly — only receive one as a prop/children from above).

## Our colocation rules (briefly — full spec in `references/colocation-rules.md`)

| Level | Path | Use case |
|---|---|---|
| L0 (default) | `app/<route>/_components/<Name>.tsx` | Used by 1 page only |
| L1 | `app/(group)/_components/<Name>.tsx` | Used by 2+ pages of same route group |
| L2 | `components/shared/<dominio>/<Name>.tsx` | Used by pages of multiple route groups |
| UI primitives | `components/ui/<name>.tsx` | shadcn/Base UI/MUI primitives |
| Theme system | `components/theme/<name>.tsx` | ThemeProvider, ModeToggle |

**Rule of Three**: stay at L0 until 3rd use, then promote. Use `promote-component` skill to automate.

## React Native specifics

- **Compound components** work identically. `<Card.Root>` + `<Card.Header>` in NativeWind, no API difference.
- **No `forwardRef`** issue (RN is React 19+ since 2024).
- **Don't lift state to `store/` automatically**: a Zustand store is for *cross-feature* state. Within a single feature, context + `useState` is correct.
- **Compound + NativeWind**: each part of a compound can have its own `className` prop. NativeWind v4 handles the compositions cleanly.

## Anti-patterns this skill flags

- ❌ 4+ boolean props on a single component → suggest compound or explicit variants.
- ❌ `renderHeader` / `renderFooter` / `renderXxx` render props → suggest children or compound.
- ❌ State managed by parent's `useState` then drilled through 3+ levels → suggest lifting to provider.
- ❌ `forwardRef` in React 19+ code → suggest plain `ref` prop.
- ❌ `useContext` in React 19+ for conditional access → suggest `use()`.
- ❌ Compound components split across files at different colocation levels → suggest unifying.
- ❌ Premature promotion of a component to L2 at the 2nd use → suggest waiting + duplicating.

## Sources

- Vercel `composition-patterns` skill: https://github.com/vercel-labs/agent-skills/tree/main/skills/composition-patterns
- Spec: `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`
- Sandi Metz, "The Wrong Abstraction": https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction
- React 19 docs: https://react.dev/reference/react
