# SmartFlow branding

Owner requested reuse of the old project's colors, icons and images in the new UI.
This is an asset/presentation exception to the fresh-project rule, not a runtime or MD migration.

## Assets used

Reference root: `C:\Users\RaywatSupaka\Documents\ChatGPT\automation-vdo 2`

| Original | New usage |
|---|---|
| `assets/smartflow_logo.png` | [Full logo](../../frontend/public/assets/brand/smartflow-logo.png) in the sidebar |
| `assets/smartflow_icon.png` | [Icon](../../frontend/public/assets/brand/smartflow-icon.png) in narrow sidebar, connection screen and favicon |
| `web_ui/ux_2026.js` shapes story/image/voice/sparkle | Static SVG artwork rendered by [BrandIcon](../../frontend/src/components/BrandIcon.tsx); no old script/controller imported |
| `web_ui/styles.css` and `web_ui/ux_2026.css` palette | Dark navy surfaces, cyan/purple accent and light text in [brand-theme.css](../../frontend/src/brand-theme.css) |

PNG files are copied unchanged. They are brand assets, not client/generated media.
No jobs, credentials, profiles or historical MD were copied. The old app and Extension remain untouched.
Native EXE icon/installer packaging is outside this UI-only change.

## Shared design tokens

`--sf-bg`, `--sf-sidebar`, `--sf-panel`, `--sf-surface`, `--sf-line`,
`--sf-text`, `--sf-muted`, `--sf-cyan`, `--sf-purple` are defined in the theme file.
The theme loads after base layout styles; the shared wizard consumes these tokens directly.
Use static React SVG components for reused artwork; never inject arbitrary SVG/HTML from provider output.

## Story header and progress

The page heading contains only `เรื่องเล่า short`; no eyebrow, subtitle or draft badge.
Each step has its circle above its label; connecting tracks run edge-to-edge between adjacent circles.
Completed stages fill the following connector and show a check; active stage uses the cyan/purple accent.
Visible numeric summaries and the separate progress track were removed at the owner's request.
Completion values remain available to assistive technology, with aria-current on the current step.
Navigation, validation and draft ownership remain in [Step wizard](step-wizard.md).
