import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Quest of the Skandhas — Srimad Bhagavatam',
  description:
    "An immersive RPG-style journey through the Srimad Bhagavatam with Sanskrit learning and Madhvacharya's teachings",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen overflow-x-hidden">{children}</body>
    </html>
  );
}
