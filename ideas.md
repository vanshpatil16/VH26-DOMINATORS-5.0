# Linear Homepage Recreation — Ground-Truth Design Spec

This is a reference-based recreation of the Linear homepage root route. The supplied screenshot and the live page at https://linear.app/ are the source of truth; fidelity to those references overrides generic landing-page conventions.

## Reference Capture

The target is Linear's dark, editorial product-development homepage. The visible navigation is a thin, nearly-black fixed header with the Linear mark and wordmark on the left, compact links for Product, Resources, Customers, Pricing, Now, Contact, a divider, Log in, and a light Sign up pill on the right. The screenshot shows the lower portion of the introductory section: oversized gray headline copy clipped by the sticky header, followed by three evenly divided figure columns labeled FIG 0.1, FIG 0.2, and FIG 0.3 with thin-line monochrome technical illustrations, headings, and muted supporting copy.

The live page establishes the broader root-route sequence: hero statement, an animated product UI presentation, social-proof/customer strip, the three-figure editorial section, an Intake and integrations feature section, additional product feature sections, customer stories, and a full footer. The recreation will preserve this hierarchy and the visible content language while using self-authored CSS/SVG illustrations and UI mockups rather than copying protected source code.

## Chosen Direction: Linear Editorial Fidelity

### Design Movement
Contemporary Swiss editorial design fused with technical systems diagrams and high-precision product UI.

### Core Principles
- Near-black surfaces and hairline separators create a quiet, instrument-like canvas.
- Typography is oversized, restrained, and left-aligned; hierarchy comes from scale, tracking, and tonal contrast rather than decoration.
- Illustrations feel like engineering drawings: thin strokes, sparse geometry, and low-contrast material surfaces.
- Product UI mockups are dense but calm, with believable controls and carefully staged motion.

### Color Philosophy
Use Linear's restrained monochrome system: #08090a / #0c0d0f for the base, cool graphite for borders, pale stone-white for primary text, and desaturated gray for secondary text. Reserve a single warm off-white for the main CTA. Accent color is intentionally absent except for tiny functional status colors inside product mockups, so the page feels focused and premium instead of promotional.

### Layout Paradigm
A long-form editorial sequence with wide, asymmetrical margins, full-bleed dark canvases, and section-specific max-widths. The navigation stays compact and horizontal while the body alternates between full-width hero compositions, centered product artifacts, and three-column figure spreads. Avoid card-heavy dashboard framing; use framed canvases, vertical rules, and generous negative space.

### Signature Elements
- Fine vertical rules dividing figure columns and feature stages.
- Technical labels such as FIG 0.1, INTAKE, BUILD, and PRODUCT DEVELOPMENT SYSTEM in mono-spaced uppercase microtype.
- A subtle radial grain and orbital linework that makes the dark background feel physical without adding visible noise.

### Interaction Philosophy
Interactions should feel like manipulating a precise instrument: small, quick, and legible. Navigation links brighten and shift by a few pixels, buttons compress slightly on press, and product UI controls respond with subtle border and surface changes. Nothing bounces or feels playful; motion should communicate system state and focus.

### Animation
- Hero headline and product canvas reveal with opacity plus a short upward transform on first load.
- Figure illustrations draw in with stroke-dashoffset and a slight float on hover.
- Product mockups transition through staged focus states with 180–260ms opacity/transform easing and a slow 12–16s ambient scan line.
- Section copy reveals as it enters the viewport using IntersectionObserver, staggered by 60ms.
- Respect prefers-reduced-motion by disabling nonessential transforms and animated linework.

### Typography System
Use `DM Sans` for interface and body copy, paired with `IBM Plex Mono` for labels and system metadata. Headlines are tight, semibold, and slightly negative-tracked. Body copy is 15–18px with generous line-height. Microtype is 11–12px with +0.12em letter spacing. Never use Inter.

### Brand Essence
A calm, high-velocity product operating system for teams building ambitious software with humans and agents. Personality: exacting, focused, quietly confident.

### Brand Voice
Headlines are declarative and compact. CTAs are direct and low-friction. Microcopy sounds like product language, not marketing filler.

Example lines:
- “The product development system for teams and agents.”
- “Plan with intent. Ship with momentum.”

### Wordmark & Logo
Use a bold geometric circular mark composed of diagonal white stripes, paired with a custom-spaced `Linear` wordmark. The mark should appear at a clearly visible size in the header and as the favicon; it must not be a generic text logo.

### Signature Brand Color
Warm mineral white `#f1f0ed`, used for the primary signup CTA and the highest-priority text against the near-black canvas.
