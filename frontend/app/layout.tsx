import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";

import "./globals.css";

import AuthGate from "./AuthGate";
import GlobalNav from "./GlobalNav";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Blinka — Agente de pagos",
  description: "Puesto de control de reglas de pago (datos sintéticos).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${inter.variable} ${geistMono.variable} font-sans antialiased`}>
        <div className="flex min-h-screen bg-paper">
          <GlobalNav />
          <div className="flex min-w-0 flex-1 flex-col">
            <main className="mx-auto w-full max-w-content flex-1 px-4 py-8 sm:px-8 sm:py-10">
              <AuthGate>{children}</AuthGate>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
