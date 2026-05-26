// Two files combined here for the example.

// FILE 1: app/_layout.tsx (root stack must declare the modal screen)
import { Stack } from "expo-router";
export function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen
        name="filters-modal"
        options={{ presentation: "modal", title: "Filters" }}
      />
    </Stack>
  );
}

// FILE 2: app/filters-modal.tsx
import { View, Text, Pressable } from "react-native";
import { useRouter } from "expo-router";

export default function FiltersModal() {
  const router = useRouter();
  return (
    <View className="flex-1 bg-white dark:bg-zinc-900 p-4 gap-4">
      <Text className="text-xl font-semibold">Filters</Text>
      {/* …filter controls… */}
      <Pressable
        onPress={() => router.back()}
        className="self-end px-4 py-2 rounded-full bg-primary"
      >
        <Text className="text-white">Apply</Text>
      </Pressable>
    </View>
  );
}

// USAGE from anywhere:
//   import { useRouter } from "expo-router";
//   const router = useRouter();
//   <Pressable onPress={() => router.push("/filters-modal")}><Text>Open</Text></Pressable>
