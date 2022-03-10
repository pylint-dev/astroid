# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Release a minor or major version

1. Release what was not yet released on the `X.Y-1` branch.
2. Remove the empty changelog for the last unreleased patch version `X.Y-1.Z'`.
3. Check the result of `git diff vX.Y-1.Z' ChangeLog`.
4. Install the release dependencies `pip3 install -r requirements_test.txt`
5. Bump the version and release by using `tbump X.Y.Z --no-push`.
6. Check the result visually and then by triggering the "release tests" workflow in
   GitHub Actions first.
7. Push the tag.
8. Release the version on GitHub with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.
9. Move back to a dev version with `tbump`:

```bash
tbump X.Y.Z+1-dev0 --no-tag --no-push  # You can interrupt after the first step
git commit -am "Upgrade the version to x.y.z+1-dev0 following x.y.z release"
```

Check the result and then upgrade the main branch

9. Delete the `X.Y-1` branch.

## Release a patch version

We release patch version when a crash or a bug is fixed on the main branch, and it needs
to be backported.

1. During the merge request on main, make sure that the changelog is for the patch
   version `X.Y-1.Z'`.
2. (Create a `X.Y-1` branch from the `X.Y-1.0` tag if it does not already exist.)
3. After the PR is merged cherry-pick the commits on the `X.Y-1` branch
4. Check the result of `git diff vX.Y-1.Z-1 ChangeLog`.
5. Install the release dependencies `pip3 install pre-commit tbump`
6. Bump the version and release by using `tbump X.Y-1.Z --no-push`.
7. Check the result visually and then by triggering the "release tests" workflow in
   GitHub Actions first.
8. Push the tag.
9. Release the version on GitHub with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.
10. Move back to a dev version with `tbump`:

```bash
tbump X.Y-1.Z+1-dev0 --no-tag --no-push  # You can interrupt after the first step
git commit -am "Upgrade the version to x.y-1.z+1-dev0 following x.y-1.z release"
```

Check the result and then upgrade the `X.Y-1` branch

13. Merge the `X.Y-1` branch on the main branch. The main branch should have the
    changelog for `X.Y-1.Z+1`. This merge is required so `pre-commit autoupdate` works
    for pylint.
14. Fix version conflicts properly, or bump the version to `X.Y.0-devZ` before pushing
    on the main branch

## Milestone handling

We move issue that were not done in the next milestone and block release only if it's an
issue labelled as blocker.
