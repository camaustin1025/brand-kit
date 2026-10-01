# DESIGN.md format (condensed)

The pack's `DESIGN.md` follows the DESIGN.md spec published by Google Labs (`github.com/google-labs-code/design.md`). Stitch lints it, the impeccable skill reads and writes it, and Lovable, v0, Bolt and Claude accept it as project knowledge. `build_pack.py` writes it; this file explains the shape so edits stay valid.

## Frontmatter (machine-readable, normative)

```yaml
---
name: Brand
description: one-line tagline
colors:
  primary: "#262323"        # one entry per token; key = descriptive slug
typography:
  display:
    fontFamily: "Brand Sans"
    fontSize: "clamp(2.5rem, 7vw, 6.4rem)"
    fontWeight: 400
    lineHeight: 0.92
    letterSpacing: "-0.05em"
  body: { ... }
rounded:
  pill: "500px"
spacing:
  md: "16px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white}"
    rounded: "{rounded.pill}"
    padding: "0.5em 2em"
    typography: "{typography.label}"
---
```

Rules:
- Token refs use `{group.key}`. Components may reference primitives. Primitives never reference each other.
- Colors: hex is the portable default. Keep an `rgb()`/`hsl()`/`oklch()` value only when the site's own source uses it as the normative form.
- Component sub-tokens are limited to eight props: `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width`. Borders, shadows, weights, hover and focus go in the prose.
- Scale keys are open. Use the brand's own names.
- Variants are naming convention: `button-primary`, `button-primary-hover`, `button-primary-active` as sibling keys.

## Body (prose, up to eight sections, fixed order)

1. `## Overview`
2. `## Colors`
3. `## Typography`
4. `## Layout`
5. `## Elevation & Depth`
6. `## Shapes`
7. `## Components`
8. `## Do's and Don'ts`

Omit a section rather than invent rules for it. Keep the canonical headings so DESIGN.md-aware tools can parse the file.

## Where the pack departs from a hand-written DESIGN.md

- Every color row in `## Colors` carries a "Measured from" column (selector and property). This is deliberate: it lets a reader trace each token back to the site.
- Inferred values are listed in `## Overview` so nobody mistakes them for measurements.
- `tokens.json` beside `DESIGN.md` holds the same tokens plus provenance and confidence for tools that prefer JSON.
