# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Process

1. Check if the dependencies of the package are correct
2. Install the release dependencies `pip3 install pre-commit copyrite tbump`
3. Bump the version and release by using `tbump X.Y.Z --no-push`. During the commit
   pre-commit and pyupgrade should remove the `encode utf8` automatically
4. Check the result and then push the tag.

Until the release is done via GitHub actions on tag, run the following commands:

```bash
git clean -fdx && find . -name '*.pyc' -delete
python3 -m venv venv
source venv/bin/activate
pip3 install twine wheel setuptools
python setup.py sdist --formats=gztar bdist_wheel
twine upload dist/*
```

## Post release

### Back to a dev version

Move back to a dev version with `tbump`:

```bash
tbump X.Y.Z-dev0 --no-tag --no-push
```

Check the result and then upgrade the master branch

### Milestone handling

We move issue that were not done in the next milestone and block release only if it's an
issue labelled as blocker.

### Files to update after releases

#### Changelog

- Create a new section, with the name of the release `X.Y.Z+1` or `X.Y+1.0` on the
  master branch.

You need to add the estimated date when it is going to be published. If no date can be
known at that time, we should use `Undefined`.

#### Whatsnew

If it's a major release, create a new `What's new in Astroid X.Y+1` document. Take a
look at the examples from `doc/whatsnew`.
