import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "GymLife",
  description: "Fitness plans, RAG coach, and streaks for beginners.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
