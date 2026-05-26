import { Pressable, Text, useColorScheme } from "react-native";
import { useState, useEffect } from "react";
import { Appearance } from "react-native";

export function DarkModeToggle() {
  const system = useColorScheme();
  const [override, setOverride] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    if (override) Appearance.setColorScheme(override);
  }, [override]);

  const current = override ?? system ?? "light";

  return (
    <Pressable
      onPress={() => setOverride(current === "dark" ? "light" : "dark")}
      className="flex-row items-center gap-2 px-4 py-2 rounded-full bg-zinc-200 dark:bg-zinc-800"
    >
      <Text className="text-zinc-900 dark:text-zinc-50">
        {current === "dark" ? "☀️ Light mode" : "🌙 Dark mode"}
      </Text>
    </Pressable>
  );
}
