import "./globals.css";

import { IBM_Plex_Sans, Space_Grotesk } from "next/font/google";

import { copy } from "@/resources/en";
import { TopNav } from "@/components/TopNav";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display"
});

const body = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-body"
});

export const metadata = {
  title: copy.appName,
  description: copy.run.title
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body>
        <TopNav />
        <main>{children}</main>
      </body>
    </html>
  );
}
