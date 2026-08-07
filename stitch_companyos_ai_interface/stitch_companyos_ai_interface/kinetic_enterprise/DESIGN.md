---
name: Kinetic Enterprise
colors:
  surface: '#0d1516'
  surface-dim: '#0d1516'
  surface-bright: '#333a3c'
  surface-container-lowest: '#080f11'
  surface-container-low: '#151d1e'
  surface-container: '#192122'
  surface-container-high: '#242b2d'
  surface-container-highest: '#2e3638'
  on-surface: '#dce4e5'
  on-surface-variant: '#bac9cc'
  inverse-surface: '#dce4e5'
  inverse-on-surface: '#2a3233'
  outline: '#849396'
  outline-variant: '#3b494c'
  surface-tint: '#00daf3'
  primary: '#c3f5ff'
  on-primary: '#00363d'
  primary-container: '#00e5ff'
  on-primary-container: '#00626e'
  inverse-primary: '#006875'
  secondary: '#c7c6cb'
  on-secondary: '#2f3034'
  secondary-container: '#46464b'
  on-secondary-container: '#b5b4ba'
  tertiary: '#ffeac0'
  on-tertiary: '#3e2e00'
  tertiary-container: '#fec931'
  on-tertiary-container: '#6f5500'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#9cf0ff'
  primary-fixed-dim: '#00daf3'
  on-primary-fixed: '#001f24'
  on-primary-fixed-variant: '#004f58'
  secondary-fixed: '#e3e2e7'
  secondary-fixed-dim: '#c7c6cb'
  on-secondary-fixed: '#1a1b1f'
  on-secondary-fixed-variant: '#46464b'
  tertiary-fixed: '#ffdf96'
  tertiary-fixed-dim: '#f3bf26'
  on-tertiary-fixed: '#251a00'
  on-tertiary-fixed-variant: '#594400'
  background: '#0d1516'
  on-background: '#dce4e5'
  surface-variant: '#2e3638'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  mono-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-margin: 24px
  gutter: 16px
  sidebar-width: 240px
  topbar-height: 56px
---

## Brand & Style

This design system is built for high-density, mission-critical operations where clarity and speed are paramount. The aesthetic is **High-Fidelity Minimalism**, drawing inspiration from precision engineering tools. It prioritizes functional beauty over decorative flourish, ensuring that AI-driven insights remain the focus of the user experience.

The target audience consists of executives, operations managers, and developers who require a "calm" interface to navigate complex data. The emotional response should be one of absolute control, reliability, and modern sophistication. 

**Core Visual Principles:**
- **Functional Density:** Information is presented compactly but with enough "breathing room" to prevent cognitive overload.
- **Precision:** Every pixel, border, and alignment is intentional, mirroring the accuracy of the underlying AI.
- **Subtle Motion:** Micro-interactions should feel instantaneous and fluid, reinforcing the system's responsiveness.

## Colors

The palette is strictly dark-mode, designed to reduce eye strain during long-form professional use. It utilizes a layered "Ink & Vapor" approach:

- **Base:** The charcoal foundation (#0A0A0B) provides a deep, non-reflective canvas.
- **Interactive:** The Cyan accent (#00E5FF) is used with extreme restraint—reserved exclusively for active states, AI processing indicators, and primary calls to action.
- **Hierarchical Grays:** Off-white (#F5F5F7) is used for headers and primary content, while Muted Gray (#86868B) is used for secondary metadata and labels to create natural visual depth without needing large font size variations.
- **Status:** Use semantic colors sparingly (Red for errors, Amber for warnings) but desaturate them slightly to fit the professional tone.

## Typography

The system uses **Inter** for its neutral, highly legible character at all scales. For technical metadata and labels, **Geist** is introduced to provide a subtle "developer-tool" aesthetic that reinforces the AI/Data nature of the platform.

**Guidelines:**
- **Tracking:** Use tighter letter spacing for large headlines to maintain a cohesive visual block.
- **Hierarchy:** Use font weight and color (Secondary Gray) rather than size to distinguish between primary and secondary information.
- **Scale:** On mobile, `display-lg` should downscale to 32px and `headline-lg` to 24px.

## Layout & Spacing

The design system employs a **Fixed-Fluid Hybrid** grid. The sidebar and navigation elements are fixed-width to ensure tool accessibility, while the main content area uses a fluid 12-column grid.

- **Rhythm:** All spacing is derived from a 4px baseline grid. Preferred increments are 8, 16, 24, 32, 48, and 64px.
- **Sidebar:** A compact 240px width that can collapse to a 64px icon-only rail.
- **Safe Zones:** A 24px outer margin is maintained on all desktop views, increasing to 32px for focused "Deep Work" views to increase white space and reduce distraction.

## Elevation & Depth

In a near-black environment, depth is communicated through **Tonal Elevation** and **Low-Contrast Outlines** rather than heavy shadows.

- **Level 0 (Base):** #0A0A0B. The background of the entire application.
- **Level 1 (Cards/Sidebar):** #1C1C1E. A subtle lift from the background. Surfaces at this level must have a 1px solid border (#2C2C2E) to define edges.
- **Level 2 (Modals/Popovers):** #2C2C2E. Used for floating elements. These are the only elements allowed to have an ambient shadow (Black, 20% opacity, 12px blur, 0px offset).
- **Glassmorphism:** Use only for the Top Bar and Sidebar background with a `backdrop-filter: blur(20px)` and 80% opacity to create a sense of layering.

## Shapes

The shape language is "Soft-Mechanical." We avoid aggressive curves to maintain a professional, systematic feel.

- **Standard Elements:** Buttons, input fields, and small cards use a 4px (`0.25rem`) corner radius.
- **Large Containers:** Dashboard widgets and primary panels use an 8px (`0.5rem`) radius.
- **Interactive Indicators:** Small 2px "pills" are used for active state markers next to menu items.
- **The Nucleus Icon:** The only perfectly circular element is the branding/AI icon, which serves as a visual anchor against the otherwise rectilinear grid.

## Components

### Buttons
- **Primary:** Solid #00E5FF with #0A0A0B text. High contrast, used for the main action only.
- **Secondary:** Transparent background with #1C1C1E border and #F5F5F7 text.
- **Ghost:** No border, secondary gray text, turns white on hover.

### Cards
- Cards must use #1C1C1E background with a #2C2C2E border. 
- Padding should be a consistent 16px or 24px.
- Header sections within cards should be separated by a 1px horizontal rule.

### Input Fields
- Background: #0A0A0B (inset look) or #1C1C1E.
- Border: 1px #2C2C2E.
- Focus State: Border color shifts to #00E5FF with a 0px offset glow.

### Sidebar & Navigation
- Active state indicated by a 2px vertical Cyan line on the far left and a subtle #FFFFFF0A background highlight.
- Text for inactive items should be #86868B.

### AI Status Indicator
- A pulsing 8px dot using a soft glow of #00E5FF. 
- When "Thinking," the Nucleus icon should rotate slowly (60s full rotation) with a variable opacity blur.