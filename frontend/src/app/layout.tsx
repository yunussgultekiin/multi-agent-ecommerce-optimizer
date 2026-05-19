import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Synapse',
  description: 'E-ticaret ürünlerinizi rakipler, fiyat, SEO ve görsel kalite açısından analiz edin.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" className="dark">
      <body className={`${inter.className} min-h-screen text-foreground antialiased selection:bg-primary/30`}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
