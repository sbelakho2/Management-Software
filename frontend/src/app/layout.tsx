import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

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
        
        {/* Screw Details */}
        <div className="fixed top-2 left-2 z-[101] hidden md:block opacity-30 select-none">
          <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
        </div>
        <div className="fixed top-2 right-2 z-[101] hidden md:block opacity-30 select-none">
          <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
        </div>
        <div className="fixed bottom-2 left-2 z-[101] hidden md:block opacity-30 select-none">
          <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
        </div>
        <div className="fixed bottom-2 right-2 z-[101] hidden md:block opacity-30 select-none">
          <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1" /><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1" /></svg>
        </div>

        {/* System Metadata Bar (Bottom) */}
        <div className="fixed bottom-0 left-0 right-0 h-8 bg-rams-chassis z-[100] border-t border-rams-border px-6 hidden md:flex items-center justify-between text-[10px] font-mono opacity-60 uppercase tracking-widest pointer-events-none">
          <div className="flex gap-6">
            <span>STATION: SENSEI-ALPHA-01</span>
            <span>OS_VER: 3.0.0-RAMS</span>
          </div>
          <div className="flex gap-6">
            <span>INTEGRITY: OPTIMAL</span>
            <span>LATENCY: 14MS</span>
          </div>
        </div>
        
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
