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
import { MotionNotice } from '@/components/ui'
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

// Runs before paint: applies the saved/system theme and motion preference so nothing flashes.
const themeScript = `try{var d=document.documentElement,t=localStorage.getItem('theme'),m=localStorage.getItem('motion');if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';d.dataset.theme=t;d.dataset.motionSource=m?'user':'system';if(!m)m=matchMedia('(prefers-reduced-motion: reduce)').matches?'reduce':'full';d.dataset.motion=m}catch(e){}`

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
          <MotionNotice />
        </body>
      </html>
    </ViewTransitions>
  )
}
