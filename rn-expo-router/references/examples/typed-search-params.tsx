// Place at: app/profile/[id].tsx
import { View, Text } from "react-native";
import { useLocalSearchParams, Link } from "expo-router";

type Params = {
  id: string;
  tab?: "info" | "posts" | "likes";
};

export default function ProfileScreen() {
  const { id, tab = "info" } = useLocalSearchParams<Params>();

  return (
    <View className="flex-1 p-4 gap-4">
      <Text className="text-xl">Profile {id}</Text>
      <Text>Active tab: {tab}</Text>

      <View className="flex-row gap-2">
        <Link href={{ pathname: "/profile/[id]", params: { id, tab: "info" } }}>
          <Text className={tab === "info" ? "font-bold" : ""}>Info</Text>
        </Link>
        <Link href={{ pathname: "/profile/[id]", params: { id, tab: "posts" } }}>
          <Text className={tab === "posts" ? "font-bold" : ""}>Posts</Text>
        </Link>
        <Link href={{ pathname: "/profile/[id]", params: { id, tab: "likes" } }}>
          <Text className={tab === "likes" ? "font-bold" : ""}>Likes</Text>
        </Link>
      </View>
    </View>
  );
}
