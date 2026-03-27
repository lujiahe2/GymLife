import type { Metadata } from "next";

import "./globals.css";

import { ChatWidgetGate } from "@/components/ChatWidget";
import { Providers } from "@/app/providers";

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
      <body>
        <Providers>
          {children}
          <ChatWidgetGate />
        </Providers>
      </body>
    </html>
  );
}
