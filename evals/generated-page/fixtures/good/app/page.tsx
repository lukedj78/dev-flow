export default function Page() {
  return (
    <main className="min-h-[100dvh] bg-[#0a0a0a] text-foreground dark:bg-background">
      <h1>Book a session</h1>
      <p>Coaching with Marina Lourenço and Tomás Capellini.</p>
      <p>marina.lourenco@studio.gym — +39 02 9876 5432</p>
      <p>Retention: 47.2% over 3,847 members</p>
      <img src="https://picsum.photos/seed/studio-hero/1200/600" alt="studio floor" />
      <button className="active:scale-[0.98] transition-transform">Sign in</button>
    </main>
  );
}
