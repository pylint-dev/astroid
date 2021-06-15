# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Process

1. Check if the dependencies of the package are correct
2. Install the release dependencies `pip3 install pre-commit tbump`
3. Bump the version and release by using `tbump X.Y.Z --no-push`.
4. Check the result.
5. Push the tag.
6. Release the version on Github with the same name as the tag and copy and paste the
   appropriate changelog in the description. This trigger the pypi release.

## Post release

### Back to a dev version

Move back to a dev version with `tbump`:

```bash
tbump X.Y.Z-dev0 --no-tag --no-push # You can interrupt during copyrite
```

Check the result and then upgrade the master branch

### Milestone handling

We move issue that were not done in the next milestone and block release only if it's an
issue labelled as blocker.

### Files to update after releases

#### Changelog

If it was a minor release add a `X.Y+1.0` title following the template:

```text
What's New in astroid x.y.z?
============================
Release Date: TBA
```

#### Whatsnew

If it was a minor release, create a new `What's new in Astroid X.Y+1` document. Take a
look at the examples from `doc/whatsnew`.
