import { View, Text, useWindowDimensions } from "react-native";
import { Image } from "expo-image";

type Props = {
  title: string;
  subtitle: string;
  imageUri: string;
};

export function ResponsiveCard({ title, subtitle, imageUri }: Props) {
  const { width } = useWindowDimensions();
  const isWide = width >= 600;

  return (
    <View
      className={
        isWide
          ? "flex-row items-center gap-4 p-4 rounded-xl bg-white dark:bg-zinc-900 shadow"
          : "flex-col gap-3 p-4 rounded-xl bg-white dark:bg-zinc-900 shadow"
      }
    >
      <Image
        source={imageUri}
        style={{ width: isWide ? 96 : 200, height: isWide ? 96 : 200, borderRadius: 8 }}
        contentFit="cover"
        placeholder={{ blurhash: "L6Pj0^jE.AyE_3t7t7R**0o#DgR4" }}
      />
      <View className="flex-1">
        <Text className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{title}</Text>
        <Text className="text-sm text-zinc-600 dark:text-zinc-400">{subtitle}</Text>
      </View>
    </View>
  );
}
