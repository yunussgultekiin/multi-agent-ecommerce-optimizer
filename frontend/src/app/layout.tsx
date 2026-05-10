import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Driven Seller Support Platform',
  description: 'AI-driven autonomous e-commerce intelligence',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
