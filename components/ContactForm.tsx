'use client'
import { useState } from 'react'
import { site } from '@/lib/site'

// No backend yet: the form composes an email in the visitor's mail app.
// TODO: swap for a real endpoint (e.g. a Next.js route handler + an email service) when you have one.
export function ContactForm() {
  const [sent, setSent] = useState(false)
  const field =
    'w-full border-b border-line bg-transparent py-3 text-lg outline-none transition-colors placeholder:text-muted focus:border-ink'

  return (
    <form
      className="space-y-8"
      onSubmit={e => {
        e.preventDefault()
        const data = new FormData(e.currentTarget)
        const subject = `Hello from ${data.get('name')}`
        const body = `${data.get('message')}\n\n${data.get('name')} · ${data.get('email')}`
        window.location.href = `mailto:${site.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
        setSent(true)
      }}
    >
      <label className="block">
        <span className="font-mono text-xs uppercase text-muted">Name</span>
        <input name="name" required autoComplete="name" className={field} placeholder="Your name" />
      </label>
      <label className="block">
        <span className="font-mono text-xs uppercase text-muted">Email</span>
        <input name="email" type="email" required autoComplete="email" className={field} placeholder="you@company.com" />
      </label>
      <label className="block">
        <span className="font-mono text-xs uppercase text-muted">Message</span>
        <textarea name="message" required rows={5} className={`${field} resize-none`} placeholder="What are you working on?" />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          className="group relative overflow-hidden rounded-[4px] border border-ink bg-ink px-6 py-4 font-display text-lg uppercase text-paper"
        >
          <span
            aria-hidden
            className="absolute inset-0 scale-0 rounded-[3px] bg-accent transition-transform duration-500 ease-[cubic-bezier(.34,1.3,.64,1)] group-hover:scale-100"
          />
          <span className="relative group-hover:text-[#111]">Write the email</span>
        </button>
        <p className="font-mono text-xs uppercase text-muted" aria-live="polite">
          {sent ? 'Your mail app should be open now.' : 'Opens your email app.'}
        </p>
      </div>
    </form>
  )
}
