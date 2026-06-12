# Product

## Register

product

## Users

Makers and hardware enthusiasts who own an Arduino UNO Q. Using the app at
home or at their desk — often at night, board lit on a workbench, phone in
hand. They are comfortable with tech; they don't need hand-holding. Primary
task on any screen: ask something of the model, or point the camera at
something and get an answer fast.

## Product Purpose

On-device conversational vision agent running entirely on the UNO Q board.
No cloud dependency. Two modes: Chat (VLM conversation, image upload) and
Detect (open-world object detection). The physical LED matrix mirrors the
app state. Success: the app disappears into the task — fast, clear, never
in the way.

## Brand Personality

Precise · Alive · Dark.

The "alive" part is carried by the hardware animation (canvas orb, LED
matrix). The app's visual surface should be precise and quiet — it does
not shout. Dark because the primary user context is a dimly lit room with
a glowing board.

## Anti-references

- Cyberpunk / neon HUD (scanlines, magenta glow, chamfered edges — the previous design)
- SaaS-cream startup (Inter on #F9FAFB, rounded-2xl, gradient hero, every YC company)
- Apple Vision Pro glass (frosted panel stacks on blurred gradients — overused)

## Design Principles

1. **The animation is the personality.** The canvas orb and LED matrix carry
   the brand's "alive" quality. The CSS surface exists to frame them cleanly,
   not to compete with them.
2. **Earned familiarity.** No invented affordances for standard tasks. Forms
   feel like forms. Buttons feel like buttons. A maker who uses Linear or
   Figma daily should feel immediately at home.
3. **Precision over decoration.** Hairline borders, tight spacing, no glow
   for glow's sake. Every visual element has a structural reason.
4. **Dark is native.** The product is built around a physical device in a
   dim-room context. Light mode is a courtesy, not the default.
5. **Information without noise.** Status, timing, labels — all present and
   readable. Nothing decorative occupies the space they could use.

## Accessibility & Inclusion

- WCAG AA minimum; AA+ where feasible (≥4.5:1 body, ≥3:1 large text).
- `prefers-reduced-motion` respected — all animations fall back to
  crossfade or instant.
- Touch targets ≥44px. No precision-required interactions.
- Color is not the only indicator — status uses both color and text label.
