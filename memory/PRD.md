# M&A Precision Mechanical Inc — PRD

## Original Problem Statement
Modern, high-converting 24/7 mobile mechanic website for **M&A Precision Mechanical Inc** (Greater Toronto Area).
Aggressive, premium, performance-inspired aesthetic (BMW M / Audi Sport).
Palette: black (#0A0A0A) + red (#E10600) + white + metallic grey accents.

## Personas
- **Stranded driver** — needs help fast, wants click-to-call + 24/7 reassurance.
- **Planning vehicle owner** — wants to schedule diagnostics/maintenance at their location.
- **Business owner (M&A)** — wants every booking emailed to `precisionfix12@gmail.com` and stored.

## Core Requirements (static)
1. Hero with logo, headline "24/7 Mobile Mechanic Service You Can Trust", phone 437-665-8384, dual CTAs.
2. 4 service cards: Inspection, Diagnostics, Repair, Maintenance (icons + hover animations).
3. About section with "we come to you" + trust pillars.
4. Functional booking form → email to `precisionfix12@gmail.com` + persist in MongoDB.
5. Contact section: click-to-call, email, GTA map placeholder, "Available 24/7".
6. Google search CTA bar linking to "M&A Mobile Mechanic" search.
7. Footer with quick links + contact.
8. Sticky header, smooth scroll, mobile-first, floating mobile Call button, red glow accents.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) + Resend (email).
  - `POST /api/bookings` — validates payload, sends Resend email to owner, persists booking. Booking succeeds even if email fails (`email_sent=false`, `email_error` captured).
  - `GET /api/bookings` — list (excludes Mongo `_id`).
  - `GET /api/health` — health probe.
- **Frontend**: React 19 + Tailwind + shadcn (Select, Calendar, Popover) + sonner (toasts) + lucide-react (icons).
- **Fonts**: Outfit (display) + Manrope (body).
- **Env**: `RESEND_API_KEY`, `SENDER_EMAIL=onboarding@resend.dev`, `OWNER_EMAIL=precisionfix12@gmail.com`.

## Implemented (2026-04-28)
- [x] Backend booking model + Resend integration (async via `asyncio.to_thread`)
- [x] MongoDB persistence with `_id` excluded from API responses
- [x] Validation: 400 on bad service type, 422 on bad email/missing fields
- [x] Hero with full-bleed image + black/red gradient overlay + brand logo glow
- [x] 4 animated service cards
- [x] About section with trust pillars + checklist
- [x] Functional booking form (date popover + time slot dropdown) with success state
- [x] Contact section with massive click-to-call number + map placeholder + pin pulse
- [x] Google search CTA with cursor-blink animation + 5-star rating
- [x] Footer with quick links + contact
- [x] Sticky header (backdrop blur on scroll) + mobile menu
- [x] Floating mobile Call Now button
- [x] Loading screen with logo pulse + red progress bar
- [x] All testIDs added; testing agent: 100% backend (10/10), 100% frontend critical flows

## Backlog
### P1
- Verify a custom domain in Resend (`resend.com/domains`) so production emails reliably reach `precisionfix12@gmail.com` without sandbox restrictions.
- Send confirmation email to the **customer** (not just the owner).
- Admin booking dashboard (read `/api/bookings`, mark statuses).

### P2
- Real Google Maps embed for service area.
- Customer testimonials carousel.
- Service-area ZIP/postal-code estimator.
- SMS notifications (Twilio) on new bookings.

## Notes
- Resend free tier without verified domain may reject deliveries to arbitrary recipients; backend tolerates this (booking still saved). To go live, verify a domain in Resend or upgrade plan.
