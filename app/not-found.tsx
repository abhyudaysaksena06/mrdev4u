import { LogoToy } from '@/components/logo/LogoToy'
import { Pill } from '@/components/ui'

export default function NotFound() {
  return (
    <section className="grid min-h-svh items-center gap-10 px-4 pt-28 pb-16 tab:grid-cols-12 tab:px-8">
      <div className="tab:col-span-5">
        <p className="font-mono text-xs uppercase text-muted">Error 404</p>
        <h1 className="display mt-3 text-[22vw] tab:text-[10rem]">Lost?</h1>
        <p className="mt-4 max-w-sm text-lg text-body">This page doesn&apos;t exist, and the logo took it badly.</p>
        <div className="mt-8">
          <Pill href="/" variant="solid" size="lg">
            Back home
          </Pill>
        </div>
      </div>
      <div className="tab:col-span-6 tab:col-start-7">
        <LogoToy mode="broken" />
      </div>
    </section>
  )
}
