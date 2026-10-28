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

## Local preview

Use Python 3.9+ and an isolated environment; the NRPE CLI does not need the
website dependency:

```sh
python3 -m venv .nrpe/site-venv
.nrpe/site-venv/bin/python -m pip install -r requirements-website.txt
.nrpe/site-venv/bin/python website/build.py
python3 -m http.server 8000 --directory .nrpe/site
```

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

Hosting uses **gh-pages**, not develop. The initial website sources remain on
`feat/github-pages-documentation`; its develop PR was closed without merging,
as requested by the maintainer. Publishing does not require integrating website
changes into develop or master. Keep that source branch while it is unmerged.

Publication requires an explicit maintainer request and an exact clean reviewed
source commit. From the separate website source branch:

```sh
.nrpe/site-venv/bin/python website/build.py
.nrpe/site-venv/bin/python website/publish.py --allow-topic
.nrpe/site-venv/bin/python website/publish.py --allow-topic --push
```

`--allow-topic` explicitly permits publishing reviewed topic sources without
integration; it does not weaken clean-checkout or asset checks. The default
is a read-only preview. `--push` checks source identity, base path,
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
stays private; Pages availability/site visibility depend on GitHub's plan and
settings. Publishing docs does not make the repository or releases public.
Review content for public disclosure; never include private logs, actual
infrastructure addresses or keys.

The connected integration returned HTTP 403 for the Pages settings API and
cannot establish or change those settings. A pushed branch alone does not
prove the website is live. Owner setup and HTTP/browser checks must complete
before claiming successful hosting. See
[GitHub Pages setup](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
