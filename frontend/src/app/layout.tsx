import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'SellerPulse AI',
  description: 'AI-driven autonomous e-commerce intelligence',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen dot-pattern text-foreground antialiased selection:bg-primary/30`}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
