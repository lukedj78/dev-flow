# Toolkit reference — TanStack Form + Zod backend

The 7 files of `lib/forms/` when `meta.json#stack.forms = "tanstack-form"`.

Dependencies:
- `@tanstack/react-form` ^1
- `zod` ^4
- shadcn `Field` component installed
- a toast primitive mounted at the root layout — shadcn's **Base UI `Toast`**
  (`components/ui/toast.tsx`, default for `--base base` since 2026-07) or **`sonner`**
  (Radix / React Aria projects). `scaffold_lib_forms.py` detects which one is installed
  and rewrites the two `// forms:toast-*` lines of `mapFormError.ts` to match.

Types verified against `@tanstack/react-form` 1.33.5 + `zod` 4.6 (FITROOM, 2026-09-22).
⚠️ Do **not** type the context as `AnyFormApi`: that is form-core's `FormApi<any…>` and has no
`Field` / `Subscribe` — those live on `ReactFormApi`, which `useForm` returns intersected with
`FormApi` as `ReactFormExtendedApi`. The toolkit exports `AnyReactFormApi` for this.

---

## `lib/forms/index.ts`

```ts
export { useEditForm } from "./useEditForm";
export { useCreateForm } from "./useCreateForm";
export { FormProvider, useFormContext } from "./FormProvider";
export { FormField } from "./FormField";
export { FormActions } from "./FormActions";
export { mapFormError, type FormErrorContext } from "./mapFormError";
```

---

## `lib/forms/FormProvider.tsx`

A thin React context wrapping the TanStack form instance so descendant `<FormField>` components can reach it without prop-drilling.

```tsx
"use client";
import { createContext, useContext, type ReactNode } from "react";
import type { ReactFormExtendedApi } from "@tanstack/react-form";

/**
 * Any form returned by `useForm`, React bindings included (`Field`, `Subscribe`).
 * Mirrors form-core's `AnyFormApi`, which drops them. The twelve generics are the
 * form data, the validators and the submit meta; TanStack declares them invariant,
 * so `any` is the only type a heterogeneous context can hold.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnyReactFormApi = ReactFormExtendedApi<any, any, any, any, any, any, any, any, any, any, any, any>;

const FormContext = createContext<AnyReactFormApi | null>(null);

export function FormProvider({
  form,
  children,
}: {
  form: AnyReactFormApi;
  children: ReactNode;
}) {
  return <FormContext.Provider value={form}>{children}</FormContext.Provider>;
}

export function useFormContext(): AnyReactFormApi {
  const ctx = useContext(FormContext);
  if (!ctx) throw new Error("useFormContext must be used inside <FormProvider>");
  return ctx;
}
```

---

## `lib/forms/useEditForm.ts`

Manual-save hook with dirty tracking + baseline reset on success. The `save` callback **must throw on failure**; errors flow through `mapFormError`.

```ts
"use client";
import { useRef } from "react";
import { useForm } from "@tanstack/react-form";
import type { z } from "zod";
import type { AnyReactFormApi } from "./FormProvider";
import { mapFormError } from "./mapFormError";

export interface UseEditFormOptions<T> {
  // Input = the form values (what TanStack validates); output is free, so
  // transforms and coercions stay allowed.
  schema: z.ZodType<unknown, T>;
  defaultValues: T;
  save: (value: T, ctx: { signal: AbortSignal }) => Promise<T>;
}

export function useEditForm<T>(opts: UseEditFormOptions<T>): AnyReactFormApi {
  // A ref, not a local: the controller must survive the re-renders between submits.
  const inFlight = useRef<AbortController | null>(null);

  return useForm({
    defaultValues: opts.defaultValues,
    validators: {
      onChange: opts.schema,
      onBlur: opts.schema,
    },
    onSubmit: async ({ value, formApi }) => {
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      try {
        const saved = await opts.save(value, { signal: controller.signal });
        // Reset baseline so isDirty returns to false; editing back to the saved
        // value leaves the form clean.
        formApi.reset(saved);
      } catch (err) {
        mapFormError(err, { form: formApi });
        throw err; // re-throw so TanStack marks submit as failed
      } finally {
        if (inFlight.current === controller) inFlight.current = null;
      }
    },
  });
}
```

---

## `lib/forms/useCreateForm.ts`

Same shape, no baseline reset; on success calls `onSuccess(result)`.

```ts
"use client";
import { useRef } from "react";
import { useForm } from "@tanstack/react-form";
import type { z } from "zod";
import type { AnyReactFormApi } from "./FormProvider";
import { mapFormError } from "./mapFormError";

export interface UseCreateFormOptions<TInput, TResult> {
  schema: z.ZodType<unknown, TInput>;
  defaultValues: TInput;
  submit: (value: TInput, ctx: { signal: AbortSignal }) => Promise<TResult>;
  onSuccess?: (result: TResult) => void;
}

export function useCreateForm<TInput, TResult>(
  opts: UseCreateFormOptions<TInput, TResult>,
): AnyReactFormApi {
  const inFlight = useRef<AbortController | null>(null);

  return useForm({
    defaultValues: opts.defaultValues,
    validators: {
      onChange: opts.schema,
      onBlur: opts.schema,
    },
    onSubmit: async ({ value, formApi }) => {
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      try {
        const result = await opts.submit(value, { signal: controller.signal });
        opts.onSuccess?.(result);
      } catch (err) {
        mapFormError(err, { form: formApi });
        throw err;
      } finally {
        if (inFlight.current === controller) inFlight.current = null;
      }
    },
  });
}
```

---

## `lib/forms/FormField.tsx`

Thin render-prop over `<form.Field name>` + shadcn `Field`/`FieldLabel`/`FieldError`. The child receives a narrowed view of the TanStack field API.

```tsx
"use client";
import { type ReactNode } from "react";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { useFormContext } from "./FormProvider";

export interface FormFieldRenderProps {
  name: string;
  value: unknown;
  setValue: (value: unknown) => void;
  onBlur: () => void;
  touched: boolean;
  isValid: boolean;
  errors: string[];
}

// Standard Schema validators (Zod) report issues as `{ message }`; function
// validators and `onServer` (mapFormError) report plain strings.
function toMessage(error: unknown): string {
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message: unknown }).message);
  }
  return "";
}

export function FormField({
  name,
  label,
  description,
  children,
}: {
  name: string;
  label: string;
  description?: string;
  children: (field: FormFieldRenderProps) => ReactNode;
}) {
  const form = useFormContext();
  return (
    <form.Field name={name}>
      {(field) => {
        const { meta } = field.state;
        const errors = meta.errors.map(toMessage).filter(Boolean);
        const invalid = meta.isTouched && !meta.isValid;
        return (
          <Field data-invalid={invalid}>
            <FieldLabel htmlFor={name}>{label}</FieldLabel>
            {children({
              name: field.name,
              value: field.state.value,
              setValue: field.handleChange,
              onBlur: field.handleBlur,
              touched: meta.isTouched,
              isValid: meta.isValid,
              errors,
            })}
            {description && <FieldDescription>{description}</FieldDescription>}
            {invalid && errors[0] && <FieldError>{errors[0]}</FieldError>}
          </Field>
        );
      }}
    </form.Field>
  );
}
```

---

## `lib/forms/FormActions.tsx`

Save + Reset button row. Reads form state via `form.Subscribe` so only this subtree re-renders on state changes.

```tsx
"use client";
import { Button } from "@/components/ui/button";
import { useFormContext } from "./FormProvider";

export function FormActions({
  submitLabel,
  submittingLabel,
  resetLabel = "Reset",
  requireDirty = true,
}: {
  submitLabel: string;
  submittingLabel: string;
  resetLabel?: string;
  requireDirty?: boolean;
}) {
  const form = useFormContext();
  return (
    <form.Subscribe
      selector={(s) => ({
        canSubmit: s.canSubmit,
        isSubmitting: s.isSubmitting,
        isDirty: s.isDirty,
      })}
    >
      {({ canSubmit, isSubmitting, isDirty }) => (
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            disabled={!isDirty || isSubmitting}
            onClick={() => form.reset()}
          >
            {resetLabel}
          </Button>
          <Button
            type="submit"
            disabled={!canSubmit || (requireDirty && !isDirty)}
          >
            {isSubmitting ? submittingLabel : submitLabel}
          </Button>
        </div>
      )}
    </form.Subscribe>
  );
}
```

---

## `lib/forms/mapFormError.ts`

Discriminated-union routing for thrown errors. Extend `switch` cases as the project's error classes evolve. **Single source of truth** for form-level error UI.

The two `// forms:toast-*` lines are the only toast-specific code. The template ships the Base UI
variant; `scaffold_lib_forms.py` swaps them for `import { toast } from "sonner"` /
`toast.error(message)` when the project has `components/ui/sonner.tsx` instead.

```ts
"use client";
import type { AnyFormApi } from "@tanstack/react-form";
import { toast } from "@/components/ui/toast"; // forms:toast-import

export interface FormErrorContext {
  // form-core's FormApi is enough here (setFieldMeta); the hooks pass `formApi`.
  form: AnyFormApi;
}

function notifyError(message: string): void {
  toast.add({ title: message, type: "error" }); // forms:toast-call
}

// Project-specific error classes (edit to match your services layer)
class SessionExpiredError extends Error {}
class ForbiddenError extends Error {}
class ValidationProblem extends Error {
  errors: Record<string, string[]>;
  constructor(errors: Record<string, string[]>) {
    super("validation");
    this.errors = errors;
  }
}
class ServerProblem extends Error {
  detail: string;
  constructor(detail: string) {
    super(detail);
    this.detail = detail;
  }
}

export function mapFormError(err: unknown, ctx: FormErrorContext): void {
  if (err instanceof SessionExpiredError) {
    // Redirect to your auth-refresh route — project-specific.
    // A full reload on purpose: it drops client state tied to the dead session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/auth/refresh");
    return;
  }
  if (err instanceof ForbiddenError) {
    notifyError("You don't have permission to perform this action.");
    return;
  }
  if (err instanceof ValidationProblem) {
    // Per-field errors — surfaced through the `onServer` slot of the error map.
    for (const [field, msgs] of Object.entries(err.errors)) {
      ctx.form.setFieldMeta(field, (meta) => ({
        ...meta,
        errorMap: { ...meta.errorMap, onServer: msgs[0] },
      }));
    }
    notifyError("Some fields need attention.");
    return;
  }
  if (err instanceof ServerProblem) {
    notifyError(err.detail);
    return;
  }
  if (err instanceof TypeError) {
    // Network failure
    notifyError("Network error. Please retry.");
    return;
  }
  notifyError("Something went wrong.");
}
```

---

## Notes

- **Adapt error classes** to your services layer. The `mapFormError` switch is the single source of truth — every form behaves identically because every form routes through it.
- **The form state stays dirty on error** so the user can fix and retry without losing edits.
- **`requireDirty` defaults to true** on `<FormActions>` for edit forms; pass `requireDirty={false}` for create forms (or split the component if your team prefers).
- **AbortController** is wired inside the hooks so re-submitting cancels the in-flight request. The button being disabled during submit is the primary defense; AbortController is the backstop for out-of-order resolution after reset.
- **i18n**: replace inline strings (`"Network error. Please retry."` etc.) with your i18n keys. The skill ships them inline; project should swap to `t("forms.errors.network")` etc.
