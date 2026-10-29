# Documentation website and GitHub Pages

The website is static HTML/CSS/JavaScript with no analytics, remote fonts,
submission database or hosted backend. Existing Markdown remains the source of
documentation. The builder rewrites internal links, creates a local search index
and checks every generated internal link/anchor. Original third-party notices
are copied without changing their text.

Presentation and field notes live under `website/`. English matches the project
documentation. The initial SLES note uses only reported observations, not an
invented testimonial or production TLS claim. New reports follow the
[field-note guide](../website/content/contributing-a-note.md).

## Homepage content and CLI capture

The product homepage, help documentation and editorial field notes use distinct
layouts from the approved design exploration. Documentation has a compact tree,
full-width blue selection, local search and a separate article outline. Field
notes feature the existing reported account and label guide links separately;
report bodies and metadata still come from canonical Markdown.

Inter Variable is self-hosted with its verbatim SIL Open Font License under
`website/assets/Inter-OFL.txt`. JetBrains Mono Regular/Bold is self-hosted for code and the browser demo with
its verbatim SIL OFL notice at `website/assets/JetBrainsMono-OFL.txt`. Ligatures
are disabled for unambiguous commands. The project mark and favicon are its own
NRPE logo; no JetBrains logo or illustrations are bundled. The former animated hero is retired with this layout.

The homepage links to GitHub's latest release rather than hardcoding a release
version. Its supported-target table is derived from the README table, keeping
target names and package formats in one source. The project story summarizes
the reported troubleshooting; it does not claim a successful production upgrade.

`website/assets/cli-help.png` shows actual `python3 nrpe.py --help` output
captured from application revision `8a2b3d33c0fa`. It is a static terminal view,
not a live session or a successful build result. Refresh it when the command
list changes: capture that command's output, render it as plain escaped text in
a local terminal-style browser view, and take a screenshot. Keep machine names,
paths and private infrastructure out of the capture. No screenshot tooling is
required to build or use the website.

`website/assets/terminal-menu.png` shows the current menu rendered by
prompt_toolkit in an empty temporary workspace. Its actual terminal screen cells
were captured at 100 columns by 24 rows and rendered as escaped text for the
screenshot. It shows no successful build or real infrastructure; the homepage
and menu guide share this image. Refresh it when navigation or presentation
changes, preserving the same empty-workspace provenance.

## Interactive browser demo

The homepage replaces its large menu image with an in-memory CLI simulation.
Users can navigate by arrows/Enter or enter the supported command subset.
Build/test phases, package state, logs and expired reports are sample data;
no shell, Docker, host access or backend runs in the browser. The demo resets
on reload, supports Escape/Ctrl+C cancellation and asks before rebuilding or
applying cleanup. Cleanup retains the sample packages and current evidence.

Maintain these examples alongside changes to the real CLI/menu. A real-browser
website test covers cancellation, rebuild consent, preview/apply cleanup,
literal input, reset and mobile layout. Without JavaScript the original menu
image remains available. The documentation sidebar uses a full-height column
with independently sticky navigation so its background meets the footer.

## FAQ structure

The [FAQ](faq.md) remains canonical Markdown: level-two headings define topics,
level-three headings define questions, and level-four headings divide longer
answers. Keep existing heading IDs stable so shared troubleshooting links work.
The website derives a compact question index, per-question links and its page
outline from these headings; answers stay visible without JavaScript.

Local search filters questions and their index entries, highlights matching
prose, and provides a clear empty/reset state. It leaves command text intact.
Opening a link to a filtered answer restores its context. The existing page
outline tracks the current section; mobile uses one content column.

## Diagrams and wide tables

Mermaid flowcharts and sequence diagrams are rendered into static SVG images
at build time with Mermaid 12.2.0 and Puppeteer 25.16.0. Install local Chrome or
Chromium on the website build workstation; set `NRPE_WEBSITE_BROWSER` to its
executable if automatic discovery does not find it. CI uses its runner's Chrome.
The browser loads Mermaid only through a temporary loopback HTTP server and
blocks other requests. Package lifecycle scripts and automatic browser downloads
remain disabled. The NRPE CLI and destination servers need none of these tools.

Diagrams use strict mode and plain SVG text; external resources, active SVG
content and per-diagram configuration overrides are rejected. Each figure has
an accessible label, a full-size link and collapsed source. Visitors need no
Mermaid runtime or JavaScript to see diagrams. Tables expose keyboard-focusable
horizontal scrolling when needed; code and URL tokens stay intact rather than
wrapping their final characters onto separate lines.

## Local preview

Fenced code blocks use **Shiki 4.5.0** with the bundled **GitHub Dark Default**
theme. Shell/Bash, PowerShell, INI, Python, YAML, JSON, Dockerfile and diff use
Shiki's existing TextMate grammars. NRPE snippets use a small project-owned
TextMate grammar for flat directives, full-line comments, `command[name]`,
`$ARGn$` and upstream build-template placeholders. General INI and NRPE files
are distinct languages; see [the configuration reference](configuration-examples.md#nrpe-file-syntax-and-upstream-defaults).

Colors and font styles come from the theme, including token background colors.
The Python builder turns tokens into scoped CSS classes so no inline style or
browser highlighter is needed. No Shiki runtime, grammar, WASM, CDN or remote font
is loaded by visitors. Code text, indentation, entities and Unicode are checked
for exact preservation before publication. Plain/unknown languages remain unchanged; Mermaid renders as static diagrams; there is no speculative language detection.

Use **Node.js 24 LTS** and **Python 3.9+** on the website build workstation.
Neither Node nor website dependencies are needed for the NRPE CLI or destination
servers. Install locked npm dependencies without package lifecycle scripts:

```sh
npm ci --prefix website --ignore-scripts --no-fund
python3 -m venv .nrpe/site-venv
.nrpe/site-venv/bin/python -m pip install -r requirements-website.txt
.nrpe/site-venv/bin/python website/build.py
python3 -m http.server 8000 --directory .nrpe/site
```

The renderer runs local Node processes with bounded timeouts and caches repeated
code batches during a build. It never downloads grammars while rendering. Missing
Node/dependencies are build errors with installation guidance, not silent plain-
text publication. CI audits both the npm lockfile and Python renderer requirements.

Open `http://localhost:8000/nrpe-custom/`. On Windows use
`.nrpe\site-venv\Scripts\python.exe` for environment-local Python commands.
The production base path is `/nrpe-custom`; builds for another path cannot be
published by the guarded publisher. Rebuilds replace only a directory carrying
this builder's manifest; arbitrary directories, unknown added files and the
workflow-state root are refused. In-checkout output belongs under
`.nrpe/site/<name>`, not `.nrpe` itself.

The [website workflow](../.github/workflows/website.yml) tests rendering, links
and publication guards and uploads a preview artifact. It never commits or
publishes automatically, preserving human-only Git authorship.

## Reviewed publication to gh-pages

Work on a topic branch, review and integrate into develop. Publication requires
a separate explicit maintainer request. From the exact clean develop or master
commit that should be shown on the website:

```sh
.nrpe/site-venv/bin/python website/build.py
.nrpe/site-venv/bin/python website/publish.py
.nrpe/site-venv/bin/python website/publish.py --push
```

The default is a read-only preview. `--push` checks source identity, base path,
all asset hashes and the human author/committer. A separate temporary Git index
creates a commit containing only the generated website, without replacing the
source checkout/index. Deployment history is appended on **gh-pages** with an
ordinary fast-forward push, never force-pushed. Concurrent changes are rejected.
Master/develop are not deployment targets and must never be deleted. Do not
develop features directly on gh-pages or edit generated HTML by hand.

The site does not update itself after a master push. Rebuild and explicitly
publish a reviewed commit when docs change; automatic package releases remain
a separate workflow.

## GitHub Pages setup by the repository owner

The requested hosting source is **gh-pages**, repository root. In GitHub:

1. Open **Settings → Pages**.
2. Select **Deploy from a branch**.
3. Select **gh-pages**, **/ (root)**, then save.
4. Wait for deployment and verify the homepage, FAQ and a deep link.

The expected URL is `https://nojokefna.github.io/nrpe-custom/`. The repository
visibility is managed by the owner and is not changed by the publisher. Pages
availability and site visibility depend on GitHub's plan and settings.
Review content for public disclosure; never include private logs, actual
infrastructure addresses or keys.

If the connected integration cannot access the Pages settings API, the owner
must complete setup in Settings. A pushed branch alone does not prove the
website is live. Deployment and HTTP/browser checks must complete before
claiming successful hosting. See
[GitHub Pages setup](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
