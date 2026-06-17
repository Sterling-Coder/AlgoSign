import type { Metadata } from "next";
import { Geist, Geist_Mono, Bricolage_Grotesque } from "next/font/google";
import "./globals.css";
import Sidebar from "./components/Sidebar";
import SearchBar from "./components/SearchBar";
import AlertToasts from "./components/AlertToasts";
import { RegionProvider } from "./components/RegionContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const display = Bricolage_Grotesque({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "AlgoSign — Worldwide Market Radar",
  description:
    "Pre-market edges radar for global retail: momentum + tokenized gap signals.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${display.variable} h-full antialiased`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('algosign.theme');if(t!=='light'){document.documentElement.classList.add('dark')}}catch(e){document.documentElement.classList.add('dark')}`,
          }}
        />
      </head>
      <body className="flex min-h-full bg-chalk text-ink">
        <RegionProvider>
          <Sidebar />
          <main className="flex-1 overflow-x-hidden">
            <header className="sticky top-0 z-10 border-b border-line bg-chalk/90 backdrop-blur">
              <div className="mx-auto flex w-full max-w-6xl items-center px-8 py-3">
                <SearchBar />
              </div>
            </header>
            <div className="mx-auto w-full max-w-6xl px-8 py-8">{children}</div>
          </main>
          <AlertToasts />
        </RegionProvider>
      </body>
    </html>
  );
}
