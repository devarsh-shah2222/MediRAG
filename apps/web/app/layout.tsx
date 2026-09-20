import type { Metadata } from "next";

import { NavBar } from "@/components/NavBar";
import { RouteLoadingOverlay } from "@/components/RouteLoadingOverlay";
import { I18nProvider } from "@/lib/i18n/I18nProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "MediRAG",
  description: "Evidence-grounded AI healthcare information and care navigation assistant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-50 text-ink-900 antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-control focus:bg-white focus:px-4 focus:py-2 focus:shadow-floating"
        >
          Skip to main content
        </a>
        <I18nProvider>
          <RouteLoadingOverlay />
          <NavBar />
          <main id="main-content" className="mx-auto max-w-5xl px-4 py-8">
            {children}
          </main>
        </I18nProvider>
      </body>
    </html>
  );
}
