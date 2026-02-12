import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { SystemMetadataBar } from '@/components/system-metadata-bar';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  title: {
    default: 'Sensei OS',
    template: '%s | Sensei OS',
  },
  description: 'Intelligent Management & Teaching System',
  applicationName: 'Sensei OS',
  keywords: ['management', 'manufacturing', 'lean', 'TPS', 'quality'],
  authors: [{ name: 'Sensei OS Team' }],
  creator: 'Sensei OS Team',
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    alternateLocale: 'fr_FR',
    title: 'Sensei OS',
    description: 'Intelligent Management & Teaching System',
    siteName: 'Sensei OS',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // Note: Do NOT set maximumScale: 1 as it prevents users from zooming for accessibility
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans antialiased relative bg-rams-chassis text-foreground`}>
        {/* Industrial Bezel Frame */}
        <div className="fixed inset-0 border-[8px] border-rams-chassis pointer-events-none z-[100] hidden md:block" aria-hidden="true" />

        {/* System Metadata Bar (Bottom) */}
        <SystemMetadataBar />
        
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
