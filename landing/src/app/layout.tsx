import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Instill — Your Own AI Engineering Platform",
  description:
    "Describe what you want to build. Instill provisions repos, generates code, and deploys to production — all on your own infrastructure with your own keys.",
  openGraph: {
    title: "Instill — Autonomous AI Engineering",
    description:
      "Open source. Bring your own keys. Describe what you want to build, we handle the rest.",
    url: "https://instill-landing.vercel.app",
    siteName: "Instill",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Instill — Autonomous AI Engineering",
    description:
      "Open source. Bring your own keys. Your own AI engineering platform.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#09090b] text-zinc-100 antialiased">
        {children}
      </body>
    </html>
  );
}
