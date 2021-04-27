# Releasing an astroid version

So, you want to release the `X.Y.Z` version of astroid ?

## Process

1. Preparation
   1. Check if the dependencies of the package are correct
   2. Put the version numbers, and the release date into the changelog
   3. Generate the new copyright notices for this release:

```bash
pip3 install copyrite
copyrite --contribution-threshold 1 --change-threshold 3 --backend-type \
git --aliases=.copyrite_aliases . --jobs=8
# During the commit pre-commit and pyupgrade will remove the encode utf8
# automatically
```

4. Submit your changes in a merge request.

5. Make sure the tests are passing on Travis/GithubActions:
   https://travis-ci.org/PyCQA/astroid/

6. Do the actual release by tagging the master with `vX.Y.Z` (ie `v1.6.12` or `v3.0.0a0`
   for example).

Until the release is done via Travis or GitHub actions on tag, run the following
commands:

```bash
git clean -fdx && find . -name '*.pyc' -delete
pip3 install twine wheel setuptools
python setup.py sdist --formats=gztar bdist_wheel
twine upload dist/*
# don't forget to tag it as well
```

## Post release

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
