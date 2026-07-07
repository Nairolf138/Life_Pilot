import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Life Pilot",
  description: "Assistant administratif et financier personnel",
};

export default function RootLayout({ children }: Readonly<{ children: import("react").ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
