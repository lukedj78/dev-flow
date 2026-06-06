# Toolkit reference — react-hook-form + Zod backend

The 7 files of `lib/forms/` when `meta.json#stack.forms = "react-hook-form"`. The **consumer-facing API is identical** to the TanStack backend — same hook names, same `<FormProvider>` / `<FormField>` / `<FormActions>` / `mapFormError`. Only the implementation differs.

Dependencies:
- `react-hook-form` ^7
- `@hookform/resolvers` ^3
- `zod` ^4
- shadcn `Field` component installed
- `sonner` mounted at the root layout

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

Wraps RHF's `FormProvider` from `react-hook-form` (it already ships one) but with our context shape so the consumer signature stays identical to the TanStack version.

```tsx
"use client";
import {
  FormProvider as RHFProvider,
  useFormContext as useRHFFormContext,
  type UseFormReturn,
} from "react-hook-form";
import { type ReactNode } from "react";

export function FormProvider({
  form,
  children,
}: {
  form: UseFormReturn<never>;
  children: ReactNode;
}) {
  return <RHFProvider {...form}>{children}</RHFProvider>;
}

export function useFormContext(): UseFormReturn<never> {
  return useRHFFormContext<never>();
}
```

---

## `lib/forms/useEditForm.ts`

Manual-save hook with dirty tracking + baseline reset. RHF tracks dirty out of the box via `formState.isDirty`; the baseline reset uses RHF's `reset(value, { keepDirty: false })`.

```ts
"use client";
import { useRef } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ZodTypeAny } from "zod/v4";
import { mapFormError } from "./mapFormError";

export interface UseEditFormOptions<T> {
  schema: ZodTypeAny;
  defaultValues: T;
  save: (value: T, ctx: { signal: AbortSignal }) => Promise<T>;
}

export function useEditForm<T>(opts: UseEditFormOptions<T>): UseFormReturn<T> {
  const inFlightRef = useRef<AbortController | null>(null);

  const form = useForm<T>({
    defaultValues: opts.defaultValues as never,
    resolver: zodResolver(opts.schema),
    mode: "onChange", // validate on change so isValid is reactive
  });

  // Wrap handleSubmit so consumers can call `form.handleSubmit()` directly
  // and the save side-effects flow through mapFormError.
  const originalHandleSubmit = form.handleSubmit;
  form.handleSubmit = ((onValid?: never, onInvalid?: never) =>
    originalHandleSubmit(
      async (value: T) => {
        inFlightRef.current?.abort();
        inFlightRef.current = new AbortController();
        try {
          const saved = await opts.save(value, {
            signal: inFlightRef.current.signal,
          });
          form.reset(saved as never, { keepDirty: false, keepValues: true });
        } catch (err) {
          mapFormError(err, { form });
          throw err;
        } finally {
          inFlightRef.current = null;
        }
        onValid?.(value as never);
      },
      onInvalid,
    )) as never;

  return form;
}
```

---

## `lib/forms/useCreateForm.ts`

Same shape, no baseline reset; on success calls `onSuccess(result)`.

```ts
"use client";
import { useRef } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ZodTypeAny } from "zod/v4";
import { mapFormError } from "./mapFormError";

export interface UseCreateFormOptions<TInput, TResult> {
  schema: ZodTypeAny;
  defaultValues: TInput;
  submit: (value: TInput, ctx: { signal: AbortSignal }) => Promise<TResult>;
  onSuccess?: (result: TResult) => void;
}

export function useCreateForm<TInput, TResult>(
  opts: UseCreateFormOptions<TInput, TResult>,
): UseFormReturn<TInput> {
  const inFlightRef = useRef<AbortController | null>(null);

  const form = useForm<TInput>({
    defaultValues: opts.defaultValues as never,
    resolver: zodResolver(opts.schema),
    mode: "onChange",
  });

  const originalHandleSubmit = form.handleSubmit;
  form.handleSubmit = ((onValid?: never, onInvalid?: never) =>
    originalHandleSubmit(
      async (value: TInput) => {
        inFlightRef.current?.abort();
        inFlightRef.current = new AbortController();
        try {
          const result = await opts.submit(value, {
            signal: inFlightRef.current.signal,
          });
          opts.onSuccess?.(result);
        } catch (err) {
          mapFormError(err, { form });
          throw err;
        } finally {
          inFlightRef.current = null;
        }
        onValid?.(value as never);
      },
      onInvalid,
    )) as never;

  return form;
}
```

---

## `lib/forms/FormField.tsx`

Render-prop bridge over RHF's `Controller`, exposing the same shape as the TanStack `FormField` so consumer code stays identical.

```tsx
"use client";
import { type ReactNode } from "react";
import { Controller, useFormContext } from "react-hook-form";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";

export function FormField({
  name,
  label,
  description,
  children,
}: {
  name: string;
  label: string;
  description?: string;
  children: (field: {
    name: string;
    value: unknown;
    setValue: (v: unknown) => void;
    onBlur: () => void;
    touched: boolean;
    isValid: boolean;
    errors: string[];
  }) => ReactNode;
}) {
  const { control } = useFormContext();
  return (
    <Controller
      control={control as never}
      name={name as never}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.isTouched && !!fieldState.error}>
          <FieldLabel htmlFor={name}>{label}</FieldLabel>
          {children({
            name: field.name,
            value: field.value,
            setValue: field.onChange,
            onBlur: field.onBlur,
            touched: fieldState.isTouched,
            isValid: !fieldState.error,
            errors: fieldState.error?.message ? [fieldState.error.message] : [],
          })}
          {description && <FieldDescription>{description}</FieldDescription>}
          {fieldState.isTouched && fieldState.error?.message && (
            <FieldError>{fieldState.error.message}</FieldError>
          )}
        </Field>
      )}
    />
  );
}
```

---

## `lib/forms/FormActions.tsx`

Save + Reset row. RHF re-renders on `formState` changes; we use `useFormState` (the targeted subscription primitive) to avoid re-rendering on unrelated fields.

```tsx
"use client";
import { useFormState, useFormContext } from "react-hook-form";
import { Button } from "@/components/ui/button";

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
  const { isDirty, isValid, isSubmitting } = useFormState({
    control: form.control,
  });
  const canSubmit = isValid && !isSubmitting;
  return (
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
  );
}
```

---

## `lib/forms/mapFormError.ts`

Identical surface to the TanStack version; only the per-field setter changes — RHF uses `setError`.

```ts
"use client";
import { toast } from "sonner";
import type { UseFormReturn } from "react-hook-form";

export interface FormErrorContext {
  form: UseFormReturn<never>;
}

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
    window.location.assign("/auth/refresh");
    return;
  }
  if (err instanceof ForbiddenError) {
    toast.error("You don't have permission to perform this action.");
    return;
  }
  if (err instanceof ValidationProblem) {
    for (const [field, msgs] of Object.entries(err.errors)) {
      ctx.form.setError(field as never, {
        type: "server",
        message: msgs[0],
      });
    }
    toast.error("Some fields need attention.");
    return;
  }
  if (err instanceof ServerProblem) {
    toast.error(err.detail);
    return;
  }
  if (err instanceof TypeError) {
    toast.error("Network error. Please retry.");
    return;
  }
  toast.error("Something went wrong.");
}
```

---

## Notes — TanStack vs RHF differences (internal only)

| Concern | TanStack Form | react-hook-form |
|---|---|---|
| Dirty tracking | `state.isDirty` (deep equal) | `formState.isDirty` (RHF tracks per field) |
| Baseline reset | `form.reset(savedValue)` | `form.reset(saved, { keepDirty: false })` |
| Per-field error from server | `setFieldMeta` + `errorMap.onServer` | `setError(field, { type: "server", message })` |
| Subscribe primitive | `form.Subscribe selector={...}` | `useFormState({ control })` |
| Field render prop | `<form.Field name>` | `<Controller name render={({field, fieldState})}>` |
| Validation trigger | Pass schema to `validators: {onChange, onBlur}` | `zodResolver(schema)` + `mode: "onChange"` |

Consumer code (the components that import `useEditForm` / `useCreateForm` / `FormField` / `FormActions`) is **identical** across both backends. That's the contract.
