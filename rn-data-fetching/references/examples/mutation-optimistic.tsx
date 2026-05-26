// app/posts/[id].tsx — post detail with optimistic like
import { Text, View, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

type Post = {
  id: string;
  title: string;
  body: string;
  likeCount: number;
  likedByMe: boolean;
};

const queryKeys = {
  posts: {
    detail: (id: string) => ["posts", "detail", id] as const,
  },
};

async function fetchPost(id: string, { signal }: { signal: AbortSignal }): Promise<Post> {
  const r = await fetch(`https://api.example.com/posts/${id}`, { signal });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

async function toggleLike(id: string): Promise<void> {
  const r = await fetch(`https://api.example.com/posts/${id}/likes`, { method: "POST" });
  if (!r.ok) throw new Error(`API ${r.status}`);
}

export default function PostDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.posts.detail(id),
    queryFn: ({ signal }) => fetchPost(id, { signal }),
  });

  const like = useMutation({
    mutationFn: () => toggleLike(id),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: queryKeys.posts.detail(id) });
      const previous = qc.getQueryData<Post>(queryKeys.posts.detail(id));
      qc.setQueryData<Post>(queryKeys.posts.detail(id), (old) =>
        old
          ? {
              ...old,
              likedByMe: !old.likedByMe,
              likeCount: old.likedByMe ? old.likeCount - 1 : old.likeCount + 1,
            }
          : old,
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(queryKeys.posts.detail(id), ctx.previous);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: queryKeys.posts.detail(id) });
    },
  });

  if (isLoading || !data) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center">
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900 p-4 gap-4">
      <Text className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
        {data.title}
      </Text>
      <Text className="text-base text-zinc-700 dark:text-zinc-300">{data.body}</Text>
      <Pressable
        onPress={() => like.mutate()}
        disabled={like.isPending}
        className="self-start flex-row items-center gap-2 px-4 py-2 rounded-full bg-zinc-100 dark:bg-zinc-800 active:opacity-80"
      >
        <Text className="text-lg">{data.likedByMe ? "❤️" : "🤍"}</Text>
        <Text className="text-zinc-900 dark:text-zinc-50">{data.likeCount}</Text>
      </Pressable>
    </SafeAreaView>
  );
}
