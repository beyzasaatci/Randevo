import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Randevo | Randevunuzu kolayca alın", description: "Berberinizden uygun saati seçin, randevunuzu zahmetsizce yönetin." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="tr"><body>{children}</body></html>;
}