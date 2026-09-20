# Third-party assets

devsheet makes **no third-party network requests at runtime**. Everything below is
vendored into the theme so that a published site depends on no CDN, leaks no visitor
IP addresses to another origin, and cannot be altered by a compromise upstream.

Update these by re-downloading the same paths at a newer version and bumping the
version recorded here.

| Asset | Version | License | Vendored at |
|-------|---------|---------|-------------|
| [KaTeX](https://katex.org) | 0.16.22 | MIT (`assets/vendor/katex.LICENSE`) | `assets/vendor/katex.min.js`, `assets/vendor/katex-auto-render.min.js`, `static/katex/` |
| [Fuse.js](https://fusejs.io) | 7.1.0 | Apache-2.0 (`assets/vendor/fuse.LICENSE`) | `assets/vendor/fuse.min.js` |
| [Crimson Pro](https://github.com/Fonthausen/CrimsonPro) | via [Fontsource](https://fontsource.org) 5.2.5 | SIL OFL 1.1 | `static/fonts/` (license in `static/fonts/OFL.txt`) |
| [Maple Mono](https://github.com/subframe7536/maple-font) | via [Fontsource](https://fontsource.org) 5.3.0 | SIL OFL 1.1 | `static/fonts/` (license in `static/fonts/OFL-maple-mono.txt`) |

## Notes

**KaTeX fonts.** Only the `woff2` format is shipped; the `woff` and `ttf` fallbacks
were stripped from `katex.min.css`. Every browser meeting this theme's baseline
supports `woff2`, and carrying three formats tripled the payload for no reader.

**Both faces are subset to `latin`** at only the styles the theme uses: Crimson Pro
at 400, 600 and 400 italic; Maple Mono at 400 and 700 (700 is what the syntax
highlighter marks keywords with).

Shipping the monospace face is deliberate. It was previously named in the CSS but
never loaded, so the theme rendered in Maple Mono only for readers who happened to
have it installed, and in the system default monospace for everyone else.

Add more files to `static/fonts/` and matching `@font-face` blocks at the top of
`assets/css/main.css` if you need other weights or scripts.

**Turning KaTeX off.** It is the largest asset here at roughly 600 KB of script and
fonts. Sites that never write math should set `math = false` under `[params]`; the
theme then emits neither the stylesheet nor the scripts.
