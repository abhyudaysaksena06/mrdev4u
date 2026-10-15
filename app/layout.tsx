import type { Metadata, Viewport } from 'next'
import localFont from 'next/font/local'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import { ViewTransitions } from 'next-view-transitions'
import { site } from '@/lib/site'
import { SmoothScroll } from '@/components/SmoothScroll'
import { Cursor } from '@/components/Cursor'
import { Nav } from '@/components/Nav'
import { Footer } from '@/components/Footer'
import './globals.css'

const anton = localFont({
  src: './fonts/anton-latin-400-normal.woff2',
  variable: '--font-anton',
  display: 'swap',
  weight: '400',
})

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: { default: `${site.alias} — ${site.role}`, template: `%s — ${site.alias}` },
  description: site.description,
  openGraph: { title: site.alias, description: site.description, type: 'website' },
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ebe9e4' },
    { media: '(prefers-color-scheme: dark)', color: '#111111' },
  ],
}

// Runs before paint so the saved or system theme never flashes.
// Also skips the preloader after the first page load of a session.
const themeScript = `try{var d=document.documentElement,t=localStorage.getItem('theme');if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';d.dataset.theme=t;if(sessionStorage.getItem('intro'))d.classList.add('no-intro');else sessionStorage.setItem('intro','1')}catch(e){}`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ViewTransitions>
      <html
        lang="en"
        className={`${anton.variable} ${GeistSans.variable} ${GeistMono.variable}`}
        suppressHydrationWarning
      >
        <head>
          <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        </head>
        <body>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
          >
            Skip to content
          </a>
          <SmoothScroll>
            <Nav />
            <main id="main" tabIndex={-1} className="outline-none">
              {children}
            </main>
            <Footer />
          </SmoothScroll>
          <Cursor />
        </body>
      </html>
    </ViewTransitions>
  )
}
