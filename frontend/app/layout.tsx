import type { Metadata } from "next";
import { DM_Sans, Source_Serif_4 } from "next/font/google";

import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600"],
});

export const metadata: Metadata = {
  title: "Blinka — Reglas vigentes",
  description: "Puesto de control de reglas de pago (datos sintéticos).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${dmSans.variable} ${sourceSerif.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
