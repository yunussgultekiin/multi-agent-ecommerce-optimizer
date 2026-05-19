import type { Metadata } from 'next';
import { Inter, Geist } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
    <html lang="tr" className={cn("dark", "font-sans", geist.variable)}>
      <body className={`${inter.className} min-h-screen text-foreground antialiased selection:bg-primary/30`}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
