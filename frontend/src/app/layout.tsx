import type { Metadata, Viewport } from 'next';
import { Plus_Jakarta_Sans, Bricolage_Grotesque } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const bricolage = Bricolage_Grotesque({
  subsets: ['latin'],
  variable: '--font-heading',
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
      <body className={`${jakarta.variable} ${bricolage.variable} font-sans antialiased relative`}>
        {/* Quirky Background Elements */}
        <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none opacity-50 dark:opacity-20">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full animate-pulse" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/20 blur-[120px] rounded-full animate-pulse [animation-delay:2s]" />
        </div>
        
        {/* Grain Overlay */}
        <div className="fixed inset-0 -z-5 pointer-events-none opacity-[0.4] mix-blend-soft-light" 
             style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
        />

        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
