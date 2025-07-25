# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Releasing a major or minor version

**Before releasing a major or minor version check if there are any unreleased commits on
the maintenance branch. If so, release a last patch release first. See
`Releasing a patch version`.**

- Remove the empty changelog for the last unreleased patch version `X.Y-1.Z'`. (For
  example: `v2.3.5`)
- Check the result of `git diff vX.Y-1.Z' ChangeLog`. (For example:
  `git diff v2.3.4 ChangeLog`)
- Install the release dependencies: `pip3 install -r requirements_minimal.txt`
- Bump the version and release by using `tbump X.Y.0 --no-push --no-tag`. (For example:
  `tbump 2.4.0 --no-push --no-tag`)
- Check the commit created with `git show` amend the commit if required.
- Move the `main` branch up to a dev version with `tbump`:

```bash
tbump X.Y+1.0-dev0 --no-tag --no-push  # You can interrupt after the first step
git commit -am "Upgrade the version to x.y+1.0-dev0 following x.y.0 release"
```

For example:

```bash
tbump 2.5.0-dev0 --no-tag --no-push
git commit -am "Upgrade the version to 2.5.0-dev0 following 2.4.0 release"
```

Check the commit and then push to a release branch:

- Open a merge request with the two commits (no one can push directly on `main`)
- After the merge, recover the merged commits on `main` and tag the first one (the
  version should be `X.Y.Z`) as `vX.Y.Z` (For example: `v2.4.0`)
- Push the tag.
- Release the version on GitHub with the same name as the tag and copy and paste the
  appropriate changelog in the description. This triggers the PyPI release.
- Delete the `maintenance/X.Y-1.x` branch. (For example: `maintenance/2.3.x`)
- Create a `maintenance/X.Y.x` (For example: `maintenance/2.4.x` from the `v2.4.0` tag.)
  based on the tag from the release. The maintenance branch are protected you won't be
  able to fix it after the fact if you create it from main.

## Backporting a fix from `main` to the maintenance branch

Whenever a PR on `main` should be released in a patch release on the current maintenance
branch:

- Label the PR with `backport maintenance/X.Y-1.x`. (For example
  `backport maintenance/2.3.x`)
- Squash the PR before merging (alternatively rebase if there's a single commit)
- (If the automated cherry-pick has conflicts)
  - Add a `Needs backport` label and do it manually.
  - You might alternatively also:
    - Cherry-pick the changes that create the conflict if it's not a new feature before
      doing the original PR cherry-pick manually.
    - Decide to wait for the next minor to release the PR
    - In any case upgrade the milestones in the original PR and newly cherry-picked PR
      to match reality.
- Release a patch version

## Releasing a patch version

We release patch versions when a crash or a bug is fixed on the main branch and has been
cherry-picked on the maintenance branch. Below, we will be releasing X.Y-1.Z (where X.Y
is the version under development on `main`.)

- Branch `release/X.Y-1.Z` off of `maintenance/X.Y.x`
- Check the result of `git diff vX.Y-1.Z-1 ChangeLog`. (For example:
  `git diff v2.3.4 ChangeLog`)
- Install the release dependencies: `pip3 install -r requirements_minimal.txt`
- Bump the version and release by using `tbump X.Y-1.Z --no-tag --no-push`. (For
  example: `tbump 2.3.5 --no-tag --no-push`. We're not ready to tag before code review.)
- Check the result visually with `git show`.
- Open a merge request against `maintenance/X.Y-1.x` to run the CI tests for this
  branch.
- Consider copying the changelog into the body of the PR to examine the rendered
  markdown.
- Wait for an approval. Avoid using a merge commit. Avoid deleting the maintenance
  branch.
- Checkout `maintenance/X.Y.x` and fast-forward to the new commit.
- Create and push the tag: `git tag vX.Y-1.Z` && `git push --tags`
- Release the version on GitHub with the same name as the tag and copy and paste the
  appropriate changelog in the description. This triggers the PyPI release.
- Freeze the main branch.
- Branch `post-X.Y-1.Z` from `main`.
- `git merge maintenance/X.Y-1.x`: this should have the changelog for `X.Y-1.Z+1` (For
  example `v2.3.6`). This merge is required so `pre-commit autoupdate` works for pylint.
- Fix version conflicts properly, meaning preserve the version numbers of the form
  `X.Y.0-devZ` (For example: `2.4.0-dev6`).
- Open a merge request against main. Ensure a merge commit is used, because pre-commit
  needs the patch release tag to be in the main branch history to consider the patch
  release as the latest version, and this won't be the case with rebase or squash. You
  can defend against trigger-happy future selves by enabling auto-merge with the merge
  commit strategy.
- Wait for approval. Again, use a merge commit.
- Unblock the main branch.
- Close the milestone and open a new patch-release milestone.

## Milestone handling

We move issues that were not done to the next milestone and block releases only if there
are any open issues labelled as `blocker`.
