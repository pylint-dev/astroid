# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Process

(Consider triggering the "release tests" workflow in GitHub Actions first.)

1. Check if the dependencies of the package are correct
2. (If you're releasing a minor (`X.Y.0`), remove the empty changelog for the last
   unreleased patch version `X.Y-1.Z'`.)
3. Check the result of `git diff vX.Y.Z-1 ChangeLog` or `git diff vX.Y-1.Z' ChangeLog`.
4. Install the release dependencies `pip3 install -r requirements_test.txt`
5. Bump the version and release by using `tbump X.Y.Z --no-push`.
6. Check the result and push the tag.
7. Release the version on GitHub with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.
8. (If you're going to release a minor (`X.Y.0`), first release what was not yet
   released on the `X.Y-1` branch then delete it.)

## Post release

### Backport fixes from main

When a crash or a bug is fixed on the main branch, and it needs to be backported:

- Make sure that the changelog is for the patch version `X.Y-1.Z'`.
- (Create a `X.Y-1` branch from the `X.Y-1.0` tag if it does not already exist.)
- After the PR is merged cherry-pick the commits on the `X.Y-1` branch
- Do a release for `X.Y-1.Z`.
- Bump `X.Y-1.Z` branch to `X.Y-1.Z+1-dev0`
- Merge the `X.Y-1` branch on the main branch. The main branch should have the changelog
  for `X.Y-1.Z+1`. (You need to merge so `pre-commit autoupdate` works.)
- Fix version conflicts properly, or bump the version to `X.Y.0-devZ` before pushing on
  the main branch

### Back to a dev version

Move back to a dev version with `tbump`:

```bash
tbump X.Y.Z+1-dev0 --no-tag --no-push # You can interrupt after the first step
git commit -am "Upgrade the version to x.y.z+1-dev0 following x.y.z release"
```

Check the result and then upgrade the main branch

### Milestone handling

We move issue that were not done in the next milestone and block release only if it's an
issue labelled as blocker.
