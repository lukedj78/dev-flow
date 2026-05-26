// app/posts/index.tsx — list of posts with TanStack Query
import { Text, View, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { FlashList } from "@shopify/flash-list";
import { useQuery } from "@tanstack/react-query";
import { Link } from "expo-router";

type Post = { id: string; title: string; author: string };

const queryKeys = {
  posts: {
    list: () => ["posts", "list"] as const,
  },
};

async function fetchPosts({ signal }: { signal: AbortSignal }): Promise<Post[]> {
  const r = await fetch("https://api.example.com/posts", { signal });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export default function PostsScreen() {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: queryKeys.posts.list(),
    queryFn: fetchPosts,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-white dark:bg-zinc-900">
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  if (isError) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-white dark:bg-zinc-900 p-4 gap-3">
        <Text className="text-red-600 dark:text-red-400">{(error as Error).message}</Text>
        <Pressable
          onPress={() => refetch()}
          className="px-4 py-2 rounded-full bg-primary"
        >
          <Text className="text-white">Retry</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900">
      <FlashList
        data={data ?? []}
        keyExtractor={(item) => item.id}
        estimatedItemSize={72}
        refreshing={isRefetching}
        onRefresh={refetch}
        renderItem={({ item }) => (
          <Link href={{ pathname: "/posts/[id]", params: { id: item.id } }} asChild>
            <Pressable className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
              <Text className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
                {item.title}
              </Text>
              <Text className="text-sm text-zinc-600 dark:text-zinc-400">
                by {item.author}
              </Text>
            </Pressable>
          </Link>
        )}
      />
    </SafeAreaView>
  );
}
