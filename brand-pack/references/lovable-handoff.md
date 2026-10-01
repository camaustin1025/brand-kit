# Handing the pack to a vibe-coding tool

The pack is tool-agnostic. `DESIGN.md` is the contract; `logo/`, `products.json` and `voice.md` are the evidence. Give the tool all of it.

## Lovable (manual, works for everyone)

1. Open or create the project.
2. Project settings, then Knowledge. Paste the entire `DESIGN.md` (frontmatter included) and save. Lovable reads Knowledge on every prompt.
3. Attach the files from `logo/` (and `products.json` when present) to the first chat message. Lovable stores attachments in the project; ask it to place logos under `public/brand/`.
4. Paste the prompt from the pack's `README.md` as the first message.
5. First render check: header logo present and unrecolored, page background equals `colors.background`, buttons match `button-primary` (fill, radius, case), headline weight and tracking match `typography.display`, no placeholder products when `products.json` exists.

## Lovable (connector, when the Lovable MCP connector is available)

- `set_project_knowledge` with the full text of `DESIGN.md`.
- `get_file_upload_url` for each logo file and `products.json`, then reference the uploads in `send_message`.
- `send_message` with the README prompt. Use `plan_mode: true` first if the project already has an established look and the user wants a review before code changes.

Only push to Lovable when the user asks. The zip is the deliverable; the push is a convenience.

## v0, Bolt, Cursor, Claude, Figma Make

Attach `DESIGN.md` and the logo files to the first message and use the same README prompt. For Figma Make or Claude Design, also paste `tokens.json` so the tool can build variables from it.

## What "on-brand" means at review time

Reject the first render when any of these is true:
- Logo recolored, stretched, replaced by text, or missing.
- Page background is pure white when `colors.background` is not.
- Buttons are rectangles when `rounded.pill` exists, or have shadows/gradients the site does not use.
- Headlines are bold or uppercase when `typography.display` says weight 400 and no transform.
- Placeholder products, lorem ipsum, or stock photos when real ones were supplied.
- A second accent color appeared that is not in `colors`.
