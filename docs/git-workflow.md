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

## Attribution

Commits carry the existing human author identity. Do not add co-author trailers,
AI attribution, or generated-with/by lines. Never rewrite old history to change
attribution. The policy check rejects invalid routes, recognizable bot identities,
missing author identities and attribution trailers. Git metadata alone cannot
prove that an author is human; maintainers must review it.

Dependabot PRs are proposals targeting `develop`, not exceptions to this policy.
Review their changes and bring approved updates onto a correctly named topic
branch with the human author's commit before integration. Do not merge bot-authored
commits or automatically merge update PRs.

## Topic branch cleanup

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
Legacy branches outside the named prefixes are not automatically removed.

## Server-side protection: one-time administrator action

The desired [ruleset](../.github/rulesets/long-lived-branches.json) protects both
long-lived branches against deletion and force-pushes, requires PRs and resolved
review threads, and requires the branch/author policy and all fast CI checks.
It does not impose an extra reviewer count on a single-maintainer repository.

The connected integration returned HTTP 403 when creating this ruleset. The
ruleset file is prepared, but server-side protection has **not** been applied
by that request. An account/token with repository administration permission must
apply it, for example from the checkout:

```sh
gh api --method POST repos/NoJokeFNA/nrpe-custom/rulesets \
  --input .github/rulesets/long-lived-branches.json
```

Alternatively import the JSON through the repository's Rules/Rulesets settings,
subject to the repository's GitHub plan and permissions. Inspect existing rules
before importing to avoid duplicates. Keep default branch `master` and global
head-branch deletion disabled. Repository settings are separate from the workflow
guards; the latter do not substitute for server-side branch protection.

See [release automation](releases.md) for what a master push does.
