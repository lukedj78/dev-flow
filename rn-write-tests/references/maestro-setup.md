> Sources: https://maestro.mobile.dev/, internal opinion.

# Maestro e2e testing setup

Maestro is the modern alternative to Detox: simpler YAML, no native build required, works with Expo Go and dev clients alike.

## 1. Install Maestro (host machine, not the app)

```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
```

Then verify: `maestro --version`. Add `~/.maestro/bin` to PATH if shell didn't.

(Optional GUI: install Maestro Studio for visual flow building.)

## 2. Folder layout in the project

```
.maestro/
├── config.yaml          # global config (optional)
├── sign-in.yaml         # one flow per file
├── add-post.yaml
└── ...
```

## 3. A flow looks like this

```yaml
# .maestro/sign-in.yaml
appId: com.yourcompany.yourapp  # from app.json#expo.ios.bundleIdentifier
---
- launchApp:
    clearState: true
- tapOn: "Sign in"
- tapOn:
    id: "email-input"           # matches testID="email-input"
- inputText: "user@example.com"
- tapOn:
    id: "password-input"
- inputText: "password123"
- tapOn: "Sign in"              # the submit button
- assertVisible: "Welcome"      # post-login screen header
```

## 4. Make components Maestro-friendly

Add `testID` to interactive elements that aren't uniquely identifiable by visible text:

```tsx
<TextInput testID="email-input" placeholder="Email" />
<TextInput testID="password-input" placeholder="Password" secureTextEntry />
```

For text-only buttons, Maestro finds them by visible text — no testID needed.

## 5. Run a flow

```bash
# iOS simulator (must be running)
maestro test .maestro/sign-in.yaml

# Android emulator
maestro test --device <serial> .maestro/sign-in.yaml

# Run all flows
maestro test .maestro/
```

## 6. Common commands

- `tapOn: "text"` or `tapOn: { id: "testID" }`
- `inputText: "..."` (after `tapOn` of an input)
- `assertVisible: "text"` / `assertNotVisible`
- `scroll` / `scrollUntilVisible`
- `swipe`
- `launchApp` / `stopApp` / `clearState`
- `back` (Android back / iOS back gesture)
- `pressKey: enter`

Full reference: https://maestro.mobile.dev/api-reference/commands

## 7. Tips

- **One flow = one user journey**. Don't pack multiple journeys in one file.
- **Use `clearState: true`** at the start of every flow that should start logged out.
- **Test on a release dev-client build**, not Expo Go, for the most realistic environment.
- **Don't assert on hardcoded values** that depend on test data — use `assertVisible: { text: ".*" }` with regex for dynamic content.
- **Run in CI** via `maestro cloud` (paid) or by running on a self-hosted emulator.

## When NOT to use Maestro

- Pure UI rendering checks → use RNTL.
- Single-component behavior → use RNTL.
- Logic without UI → plain Jest.
- Maestro is the ONLY tool for: navigation across multiple screens, deep linking, push notification tapping, native camera/photo-picker interaction.
