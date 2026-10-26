import type { NextConfig } from 'next'

// The TEDxTIET 2026 site, at www.mrdev4u.com/tedxtiet. It is its own Vercel
// project (tedxtiet); these rewrites proxy the path onto it, so the address bar
// keeps showing mrdev4u.com. That deployment answers /tedxtiet/... itself, with
// a page built for the prefix (see vercel.json and vite.config.ts there).
const TEDXTIET = 'https://tedxtiet-gamma.vercel.app'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: '/tedxtiet', destination: `${TEDXTIET}/tedxtiet` },
      { source: '/tedxtiet/:path*', destination: `${TEDXTIET}/tedxtiet/:path*` },
    ]
  },
}

export default nextConfig
