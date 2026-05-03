import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Powerhouse — Build a business in 5 minutes",
  description:
    "Describe your business. AI builds everything — storefront, payments, inventory, marketing. Live in minutes. Self-healing forever.",
  openGraph: {
    title: "Powerhouse — Build a business in 5 minutes",
    description:
      "AI that builds, deploys, monitors, and heals your entire business. Not just code.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="bg-[#0a0a0f] text-[#e4e4e7] antialiased">
        {children}
      </body>
    </html>
  );
}
