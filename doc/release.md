# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Releasing a major or minor version

**Before releasing a major or minor version check if there are any unreleased commits on
the maintenance branch. If so, release a last patch release first. See
`Release a patch version`.**

1. Remove the empty changelog for the last unreleased patch version `X.Y-1.Z'`. (For
   example: `v2.3.5`)
2. Check the result of `git diff vX.Y-1.Z' ChangeLog`. (For example:
   `git diff v2.3.4 ChangeLog`)
3. Install the release dependencies: `pip3 install -r requirements_test.txt`
4. Bump the version and release by using `tbump X.Y.0 --no-push`. (For example:
   `tbump 2.4.0 --no-push`)
5. Check the result visually and then by triggering the "release tests" workflow in
   GitHub Actions first.
6. Push the tag.
7. Release the version on GitHub with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.
8. Move the `main` branch up to a dev version with `tbump`:

```bash
tbump X.Y+1.0-dev0 --no-tag --no-push  # You can interrupt after the first step
git commit -am "Upgrade the version to x.y+1.0-dev0 following x.y.0 release"
```

For example:

```bash
tbump 2.5.0-dev0 --no-tag --no-push
git commit -am "Upgrade the version to 2.5.0-dev0 following 2.4.0 release"
```

Check the result and then upgrade the main branch

11. Delete the `maintenance/X.Y-1.x` branch. (For example: `maintenance/2.3.x`)

## Backporting a fix from `main` to the maintenance branch

Whenever a commit on `main` should be released in a patch release on the current
maintenance branch we cherry-pick the commit from `main`.

1. During the merge request on `main`, make sure that the changelog is for the patch
   version `X.Y-1.Z'`. (For example: `v2.3.5`)
2. Create a `maintenance/X.Y.x` branch on Github --if it does not already exist-- from
   the `X.Y-1.0` tag . (For example: `maintenance/2.3.x` from the `v2.3.0` tag.)
3. After the PR is merged on `main` cherry-pick the commits on the `maintenance/X.Y.x`
   branch (For example: from `maintenance/2.4.x` cherry-pick a commit from `main`)
4. Release a patch version

## Releasing a patch version

We release patch version when a crash or a bug is fixed on the main branch and has been
cherry-picked on the maintenance branch.

4. Check the result of `git diff vX.Y-1.Z-1 ChangeLog`. (For example:
   `git diff v2.3.4 ChangeLog`)
5. Install the release dependencies: `pip3 install -r requirements_test.txt`
6. Bump the version and release by using `tbump X.Y-1.Z --no-push`. (For example:
   `tbump 2.3.5 --no-push`)
7. Check the result visually and then by triggering the "release tests" workflow in
   GitHub Actions first.
8. Push the tag.
9. Release the version on GitHub with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.
10. Move the `main` branch up to a dev version with `tbump`:

```bash
tbump X.Y.Z+1-dev0 --no-tag --no-push  # You can interrupt after the first step
git commit -am "Upgrade the version to x.y.z+1-dev0 following x.y.z release"
```

For example:

```bash
tbump 2.3.6-dev0 --no-tag --no-push
git commit -am "Upgrade the version to 2.3.6-dev0 following 2.3.5 release"
```

Check the result and then upgrade the `maintenance/X.Y.x` branch

13. Merge the `maintenance/X.Y.x` branch on the main branch. The main branch should have
    the changelog for `X.Y-1.Z+1` (For example `v2.3.6`). This merge is required so
    `pre-commit autoupdate` works for pylint.
14. Fix version conflicts properly, or bump the version to `X.Y.0-devZ` (For example:
    `2.4.0-dev6`) before pushing on the main branch

## Milestone handling

We move issues that were not done to the next milestone and block releases only if there
are any open issues labelled as `blocker`.
