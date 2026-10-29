# Branches, commits and integration

`master` is the default and release branch. `develop` is the integration branch.
**Never delete either branch.** New work starts from current `develop` on one
of `feat/...`, `fix/...`, `refactor/...`, or `remove/...`.

```sh
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feat/example
# Make and test the change, then stage explicit paths and commit.
git push -u origin feat/example
gh pr create --base develop
```

Use a PR/MR into `develop`. Promote the tested integration branch using a PR
from `develop` into `master`; never route a topic directly into `master`.
Prefer a normal merge for develop-to-master promotion so ancestry remains clear.
Keep working on topic branches, not directly on either long-lived branch.

Integration ends at `develop` by default. Create or merge a develop-to-master
promotion PR only when the maintainer explicitly requests promotion to master.
A request to implement a change or integrate it into develop does not authorize
a master PR or release. Once an explicitly requested promotion reaches master,
the automatic release workflow runs as configured.

By default, work remains on a local topic branch. Pushing, opening a PR or
merging into develop requires an explicit maintainer request. Master promotion
requires its own explicit request. Complete the current change and checks before
starting the next integration.

## Attribution

Authored work carries the existing human author identity. Do not add co-author trailers,
AI attribution, or generated-with/by lines. Never rewrite old history to change
attribution. The policy check rejects invalid routes, recognizable bot identities,
missing author identities and attribution trailers. Git metadata alone cannot
prove that an author is human; maintainers must review it.

Genuine Dependabot PRs into `develop` are the sole approved bot exception.
The policy checks GitHub's PR event for the official `dependabot[bot]` login,
numeric identity and Bot account type, a `dependabot/...` head, and the same
repository on both sides. The event's refs and SHAs must match the checked PR.
Only Dependabot's exact official author name/email are exempted; arbitrary bots,
AI attribution and co-author/generated-with trailers remain prohibited.

Review update diffs, upstream release notes and compatibility checks before
merging a Dependabot PR directly into `develop`. Do not enable automatic merges.
Accepted Dependabot commits remain valid during a subsequent same-repository
`develop`-to-`master` promotion. A bot branch cannot target master directly.

## Topic branch cleanup

`gh-pages` is the website deployment branch, not a topic branch. Website sources
follow the normal topic-to-develop review flow; an explicitly requested
publication appends a human-authored generated-site commit to gh-pages. It does
not promote develop to master. See [website publication](website.md).

Leave GitHub's unrestricted **Automatically delete head branches** setting off.
It cannot express the required distinction between topic branches and the
long-lived `develop` head of a promotion PR.

The cleanup workflow handles successful merges into `develop` only. It requires
an eligible topic prefix, the same repository, no other open PR needing the head,
and an unchanged head SHA. Deletion uses a Git lease so a concurrent push is not
deleted accidentally. Unmerged/closed PRs, forks, changed heads and unknown branch
prefixes are retained. `master` and `develop` are always excluded.

After a successful merge, update local `develop`, inspect local changes and PR
state, and remove the corresponding local topic only when its work is integrated.
Never use `gh pr merge --delete-branch` for a develop-to-master promotion.
Successfully merged genuine Dependabot branches use the same guarded cleanup,
including the unchanged-head lease and open-PR checks. Other branches outside
the named prefixes are not automatically removed.

## Server-side protection: one-time administrator action

The [ruleset template](../.github/rulesets/long-lived-branches.json) protects both
long-lived branches against deletion and force-pushes, requires PRs and resolved
review threads, and requires the branch/author policy and all fast CI checks.
It does not impose an extra reviewer count on a single-maintainer repository.

Protection was applied by the repository owner and verified on 2026-10-27:
[active ruleset 25987752](https://github.com/NoJokeFNA/nrpe-custom/rules/25987752)
targets `refs/heads/master` and `refs/heads/develop`, with no bypass actors.
Both branches have deletion/force-push protection, PR and resolved-thread
requirements, and all six fast status checks from the template. The default
branch remains `master`; unrestricted automatic head-branch deletion is off.

Inspect effective rules when checking or changing repository settings:

```sh
gh api repos/NoJokeFNA/nrpe-custom/rules/branches/master
gh api repos/NoJokeFNA/nrpe-custom/rules/branches/develop
```

For a new repository, an administrator can apply the template through GitHub's
Rules/Rulesets settings or API, subject to plan and permissions. The connected
integration returned HTTP 403 for administrative writes; owner configuration
was required. Inspect existing rules before applying a template to avoid
duplicates. Keep both target branches selected, the ruleset active, default
branch `master` and global head-branch deletion disabled. Repository settings
are separate from workflow guards; verify both rather than assuming that a
committed template establishes protection.

See [release automation](releases.md) for what a master push does.
