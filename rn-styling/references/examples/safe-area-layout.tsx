import { ScrollView, View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

type Props = { title: string; children: React.ReactNode };

export function SafeAreaScreen({ title, children }: Props) {
  return (
    <SafeAreaView
      className="flex-1 bg-white dark:bg-zinc-900"
      edges={["top", "bottom"]}
    >
      <View className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <Text className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          {title}
        </Text>
      </View>
      <ScrollView className="flex-1" contentContainerClassName="p-4 gap-4">
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
