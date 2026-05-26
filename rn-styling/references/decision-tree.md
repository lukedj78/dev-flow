> Sources: NativeWind v4 docs, internal opinion.

# Decision tree — styling

## Q1: StyleSheet, NativeWind, or inline?

```
Is the style per-frame animated (gets read 60 times/sec)?
├── YES → StyleSheet (avoid string parsing overhead). Use Reanimated worklets if it's animated state.
└── NO  → NativeWind. Default for everything else.

Is the style derived from JS state (e.g. width based on a prop)?
├── YES with a *small* dynamic piece → inline style for the dynamic part:
│         className="rounded-lg" style={{ width: dynamicWidth }}
└── YES with mostly static → use NativeWind variants:
         className={cn("rounded-lg", isLarge && "p-8", isSmall && "p-2")}
```

## Q2: How do I make this responsive?

```
Need it to differ on phone vs tablet?
├── YES → useWindowDimensions() in the component, branch on width.
│        // No tailwind breakpoints in RN — NativeWind v4 supports them but RN ecosystem
│        // is mostly phone-sized; keep responsive logic in JS.
└── NO  → just write the design.
```

## Q3: Dark mode — do I need to wire anything?

```
Is the project already set up by rn-bootstrap?
├── YES → just use `dark:` variants. NativeWind reads useColorScheme() automatically.
└── NO  → add `darkMode: 'class'` in tailwind.config.js + wrap root with
         NativeWind colorScheme provider. See nativewind-setup.md.
```

## Q4: I need a value that's not in tailwind.config.js

```
Is the value going to be reused?
├── YES → add it to tailwind.config.js (and DESIGN.md upstream).
└── NO  → arbitrary value: className="p-[13px]" or className="bg-[#abc123]"
         (allowed sparingly; if you do this more than twice for the same value,
         go back to "YES").
```
