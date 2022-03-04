# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Process

(Consider triggering the "release tests" workflow in GitHub Actions first.)

1. Check if the dependencies of the package are correct
2. Check the result (Do `git diff vX.Y.Z-1 ChangeLog` in particular).
3. Install the release dependencies `pip3 install -r requirements_test.txt`
4. Bump the version and release by using `tbump X.Y.Z --no-push`.
5. Push the tag, push a `X.Y` branch.
6. Release the version on GitHub with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.

## Post release

### Backport fixes from main

When a crash or a bug is fixed on the main branch, and it needs backport, make sure that
the changelog is for the patch version `X.Y-1.Z'` then after the PR is merged
cherry-pick the commit on the `X.Y-1` branch and do a release for `X.Y-1.Z`.

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
