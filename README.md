# mrdev4u

Portfolio site: Grigoletti-style editorial layout and motion, an "m/" logo that
assembles in the preloader and lives in the nav, a doodle of me as the hero element,
and a playable 3D version of the logo on the 404 page.

Built with Next.js 16, React 19, Tailwind CSS 4, Motion, Lenis and React Three Fiber.

## Run it

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production build (all pages are static)
npm run typecheck
```

## Make it yours

| What | Where |
| --- | --- |
| Name, alias, footer wordmark, email, time zone, socials, toolkit, services, values | `lib/site.ts` |
| Projects and case studies (two are placeholders) | `lib/projects.ts` |
| Hero headline and intro | `app/page.tsx` |
| About copy and portrait | `app/about/page.tsx` |
| Colours, easing curves, grain | `app/globals.css` |
| Logo shape (shared by the SVG and the 3D model) | `components/logo/geometry.ts` |

Change the logo by editing the five pieces in `geometry.ts`; the SVG mark, favicon generator,
preloader and 3D model all read from it. Regenerate `app/icon.svg` if you change it.

## How the motion works

- **Intro:** pure CSS (`Intro timeline` in `globals.css`), so it starts at first paint: the m/ logo's
  pieces fly together while a counter runs, then the curtain lifts. It plays on every full load of
  the home page and is skipped when you navigate back to home inside the site.
- **Motion preference:** `<html data-motion="full|reduce">`, set before paint from the visitor's saved
  choice or their OS setting. The nav's *Motion* toggle overrides it, and visitors whose OS has
  animations off get a one-time notice offering to turn motion on. Reduced mode keeps a short, still
  preloader, fades instead of slides, no smooth scroll, and a 3D logo without idle spin.
- **One curve:** `--ease-out: cubic-bezier(0.12, 0.23, 0.5, 1)`, measured from grigoletti.ch.
- **3D logo toy:** `components/logo/` (404 page). Loads only on interaction, on devices
  with WebGL2 and no data-saver setting. Everyone else gets the SVG mark.
- **Doodle:** a 3D model of the reference drawing, built, rigged and animated in Blender by
  `scripts/doodle-3d/` (`build_model.py` model and rig, `anim_wave.py` the wave, `check.py` the
  review harness). The hero (`HeroDoodle.tsx`) shows a still render (`public/doodle3d/rest.webp`)
  and plays the rendered wave over it after the preloader and on every click: an H.264/VP9 video
  with the colour in the top half and the alpha matte in the bottom half, recombined on a WebGL
  canvas (small, and transparent in every browser).
- **Smooth scroll:** Lenis on fine-pointer devices only.
- **Page transitions:** View Transitions API via `next-view-transitions`; project covers morph
  into the case-study hero.

## Measured (Lighthouse 12.8, mobile preset, local production build)

| Page | Performance | Accessibility | Best practices | SEO |
| --- | --- | --- | --- | --- |
| Home | 89–93 | 100 | 100 | 100 |
| Work | 93 | 100 | 100 | 100 |
| Case study | 91 | 100 | 100 | 100 |
| About | 94 | 100 | 100 | 100 |
| Contact | 96 | 100 | 100 | 100 |
