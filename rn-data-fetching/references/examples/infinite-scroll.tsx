// app/feed.tsx — infinite scroll with FlashList + useInfiniteQuery
import { Text, ActivityIndicator, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery } from "@tanstack/react-query";

type Post = { id: string; title: string };
type Page = { items: Post[]; nextCursor: number | null };

const queryKeys = {
  posts: {
    feed: () => ["posts", "feed"] as const,
  },
};

async function fetchFeedPage(
  cursor: number,
  { signal }: { signal: AbortSignal },
): Promise<Page> {
  const r = await fetch(`https://api.example.com/posts?cursor=${cursor}&limit=20`, { signal });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export default function FeedScreen() {
  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
    isRefetching,
  } = useInfiniteQuery({
    queryKey: queryKeys.posts.feed(),
    queryFn: ({ pageParam, signal }) => fetchFeedPage(pageParam, { signal }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center">
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  const items = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900">
      <FlashList
        data={items}
        keyExtractor={(item) => item.id}
        estimatedItemSize={72}
        refreshing={isRefetching}
        onRefresh={refetch}
        onEndReached={() => {
          if (hasNextPage && !isFetchingNextPage) fetchNextPage();
        }}
        onEndReachedThreshold={0.5}
        renderItem={({ item }) => (
          <View className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
            <Text className="text-base text-zinc-900 dark:text-zinc-50">{item.title}</Text>
          </View>
        )}
        ListFooterComponent={
          isFetchingNextPage ? (
            <View className="py-4 items-center">
              <ActivityIndicator />
            </View>
          ) : null
        }
      />
    </SafeAreaView>
  );
}
