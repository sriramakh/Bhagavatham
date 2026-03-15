import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Quest of the Skandhas — Srimad Bhagavatam',
  description:
    "An immersive RPG-style journey through the Srimad Bhagavatam with Sanskrit learning and Madhvacharya's teachings",
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen overflow-x-hidden">{children}</body>
    </html>
  );
}
