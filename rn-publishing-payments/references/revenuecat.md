> Sources: https://www.revenuecat.com/docs/getting-started/installation/reactnative

# RevenueCat — recommended IAP SDK

RevenueCat sits between your client and StoreKit / Google Play Billing. It handles receipt validation, cross-platform subscription state, restore-purchases, A/B price testing, and analytics. Free tier: 10k MTR (monthly tracked revenue) — generous.

## 1. Install

```bash
npx expo install react-native-purchases react-native-purchases-ui -- --legacy-peer-deps
```

For RN Firebase / Hermes / New Architecture, `react-native-purchases` works since v8+ — install the current v10 (10.6.0, same for `react-native-purchases-ui`). Verify with `npm view react-native-purchases peerDependencies`. `react-native-purchases-ui` (RevenueCatUI) ships prebuilt, remotely-configurable Paywalls and a Customer Center — the recommended default over a hand-rolled paywall (see step 5).

## 2. RevenueCat dashboard setup (one-time)

1. Create app on https://app.revenuecat.com.
2. Connect App Store Connect (paste a shared secret from ASC → Apps → Your app → App Information).
3. Connect Google Play (upload service account JSON — same as `eas submit`).
4. Create Products: e.g. `premium_monthly` (€4.99/month), `premium_annual` (€39.99/year). RevenueCat creates them in ASC + Play.
5. Create Entitlements: e.g. `pro`. Attach products to it.
6. Create Offerings: a "default" offering with `premium_monthly` + `premium_annual` packages.

## 3. `lib/purchases.ts`

```ts
import Purchases, { CustomerInfo } from "react-native-purchases";
import { Platform } from "react-native";

const IOS_KEY = process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY!;
const ANDROID_KEY = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY!;

export async function initPurchases(appUserId: string) {
  Purchases.configure({
    apiKey: Platform.select({ ios: IOS_KEY, android: ANDROID_KEY })!,
    appUserID: appUserId, // YOUR user ID, so RC links purchases to your account
  });
}

export async function getOfferings() {
  const offerings = await Purchases.getOfferings();
  return offerings.current; // the default offering
}

export async function purchasePackage(pkg: import("react-native-purchases").PurchasesPackage) {
  const { customerInfo } = await Purchases.purchasePackage(pkg);
  return customerInfo;
}

export async function restorePurchases(): Promise<CustomerInfo> {
  return await Purchases.restorePurchases();
}

export function hasEntitlement(info: CustomerInfo, key: string): boolean {
  return info.entitlements.active[key] !== undefined;
}
```

## 4. Initialize on sign-in

```ts
// In your sign-in success handler (lib/auth.ts)
import { initPurchases } from "./purchases";

const onSignIn = async (user) => {
  await initPurchases(user.id);
};
```

Pass YOUR user id as `appUserID`. RevenueCat links the purchase to that id, so when the user signs in on a different device with the same account, their subscription follows.

## 5. Paywall screen

**Recommended default: RevenueCatUI's prebuilt Paywall.** Instead of hand-rolling the UI, render `<RevenueCatUI.Paywall />` (or present it with `RevenueCatUI.presentPaywall()`). The paywall is designed and A/B-tested from the RevenueCat dashboard — no app release needed to change copy, pricing layout, or the offering — and it wires up purchase + restore for you.

```tsx
// app/(app)/paywall.tsx (RevenueCatUI — recommended)
import RevenueCatUI from "react-native-purchases-ui";

export default function Paywall() {
  return (
    <RevenueCatUI.Paywall
      onPurchaseCompleted={({ customerInfo }) => {
        if (customerInfo.entitlements.active.pro) {
          // navigate or invalidate queries
        }
      }}
      onRestoreCompleted={({ customerInfo }) => {
        // handle restored entitlements
      }}
    />
  );
}
```

RevenueCatUI also ships a **Customer Center** (`RevenueCatUI.presentCustomerCenter()`) for self-serve manage/cancel/refund flows.

The hand-rolled paywall below remains valid when you need full custom UI:

```tsx
// app/(app)/paywall.tsx (hand-rolled — when you need custom UI)
import { useEffect, useState } from "react";
import { Text, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { getOfferings, purchasePackage } from "@/lib/purchases";
import type { PurchasesOffering } from "react-native-purchases";

export default function Paywall() {
  const [offering, setOffering] = useState<PurchasesOffering | null>(null);
  const [purchasing, setPurchasing] = useState(false);

  useEffect(() => {
    getOfferings().then(setOffering);
  }, []);

  if (!offering) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center">
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-background dark:bg-background-dark p-4 gap-4">
      <Text className="text-2xl font-semibold">Go Pro</Text>
      <Text className="text-base text-zinc-700 dark:text-zinc-300">
        Unlock advanced features…
      </Text>

      {offering.availablePackages.map((pkg) => (
        <Pressable
          key={pkg.identifier}
          onPress={async () => {
            setPurchasing(true);
            try {
              const info = await purchasePackage(pkg);
              if (info.entitlements.active.pro) {
                // navigate or invalidate queries
              }
            } catch (e: any) {
              if (!e.userCancelled) {
                // show error
              }
            } finally {
              setPurchasing(false);
            }
          }}
          disabled={purchasing}
          className="px-4 py-4 rounded-xl bg-primary active:opacity-80 disabled:opacity-50"
        >
          <Text className="text-white font-semibold">
            {pkg.product.title} — {pkg.product.priceString}
          </Text>
        </Pressable>
      ))}

      <Pressable onPress={async () => {
        // mandatory: "Restore Purchases" button on every paywall
        const info = await import("@/lib/purchases").then((m) => m.restorePurchases());
        // …
      }}>
        <Text className="text-center text-zinc-600">Restore purchases</Text>
      </Pressable>
    </SafeAreaView>
  );
}
```

**Apple requires a Restore Purchases button** visible on the paywall (guideline 3.1.1). Skip and reject.

## 6. Gating features

```ts
// hooks/usePro.ts
import { useQuery } from "@tanstack/react-query";
import Purchases from "react-native-purchases";

export function usePro() {
  return useQuery({
    queryKey: ["purchases", "customerInfo"],
    queryFn: async () => {
      const info = await Purchases.getCustomerInfo();
      return {
        isPro: info.entitlements.active.pro !== undefined,
        expiresAt: info.entitlements.active.pro?.expirationDate,
      };
    },
    staleTime: 5 * 60_000,
  });
}

// In a screen
const { data } = usePro();
if (!data?.isPro) return <Redirect href="/(app)/paywall" />;
```

## 7. Testing

- iOS: create a Sandbox Apple ID in ASC → Users and Access → Sandbox Testers. Sign in on the device's Settings → App Store. Then your app's IAP triggers a sandbox flow with that account.
- Android: add yourself as an internal tester in Play Console. Same email signs in on the device, then IAP triggers test purchases.

RevenueCat's dashboard shows both sandbox and production transactions clearly separated.

## 8. Common pitfalls

- **`appUserID` not set**: purchases attach to an anonymous device ID; user can't restore on another device.
- **Forgetting `expo-build-properties`** for iOS `useFrameworks: "static"`: required for `react-native-purchases` v10.
- **No "Restore Purchases" button**: Apple reject 3.1.1.
- **Subscription auto-renew off in sandbox**: Apple's sandbox subscriptions renew every few minutes for testing — expected.
- **`getCustomerInfo()` cached too long**: if the user just purchased, force a refresh with `Purchases.invalidateCustomerInfoCache()`.
