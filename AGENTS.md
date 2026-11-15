# Agent guidelines

## Before opening a pull request

### Check for existing work

Do this twice: before you start working on an issue, and again right before you open
your pull request. Someone may have opened one in between.

**Rule: if the issue already has an `OPEN` pull request, do not open another one.**
Review that pull request or suggest improvements on it instead. Two pull requests for
the same fix waste review time, and one of them will be closed.

#### Step 1: list the pull requests linked to the issue

On GitHub, the pull requests that will close an issue appear in the "Development" box of
the issue's sidebar. Get that list with this command. Only change `3257` to your issue
number:

```shell
gh api graphql -F number=3257 -f query='
query($number: Int!) {
  repository(owner: "pylint-dev", name: "astroid") {
    issue(number: $number) {
      closedByPullRequestsReferences(first: 50, includeClosedPrs: true) {
        nodes { number state url author { login } }
      }
    }
  }
}' --jq '.data.repository.issue.closedByPullRequestsReferences.nodes[] | "\(.state) \(.url) by \(.author.login)"'
```

Each output line is one pull request. Example output:

```text
CLOSED https://github.com/pylint-dev/astroid/pull/3264 by arunsoman
OPEN https://github.com/pylint-dev/astroid/pull/3297 by 00200200
OPEN https://github.com/pylint-dev/astroid/pull/3329 by nabhan06
```

- A line starting with `OPEN`: someone is already working on it. Stop and follow the
  rule above.
- `MERGED`: the fix may already be on `main`. Check whether the bug still happens there.
- `CLOSED`: that attempt was abandoned. Read why before you start, so you do not repeat
  it.
- No output at all: no pull request is linked. Go to step 2.

If `gh` is not installed or not logged in, read the same data from the issue's web page.
It works without a GitHub account. Only change `3257` to your issue number:

```shell
curl -sL https://github.com/pylint-dev/astroid/issues/3257 | python3 -c '
import json, sys
page = sys.stdin.read()
key = "\"closedByPullRequestsReferences\":"
start = page.find(key)
if start == -1:
    sys.exit("Development data not found: is this an issue URL, not a pull request URL?")
data, _ = json.JSONDecoder().raw_decode(page, start + len(key))
for pr in data["nodes"]:
    print(pr["state"], pr["url"])
'
```

The output and its meaning are the same as above, without the author.

#### Step 2: search for pull requests that are not linked

Step 1 only finds pull requests that say `Closes #<number>` (or `Fixes`, `Resolves`), or
that a maintainer linked by hand. A pull request that only mentions the issue, or forgot
to mention it, is not in that list. Search for those too:

```shell
gh pr list --repo pylint-dev/astroid --state open --search "3257"
gh pr list --repo pylint-dev/astroid --state open --search "<key words from the issue title>"
```

#### Step 3: check if someone said they are working on it

List the issue's comments with their dates. Only change `3257` to your issue number:

```shell
gh issue view 3257 --repo pylint-dev/astroid --json comments --jq '.comments[] | "\(.createdAt[:10]) \(.author.login): \(.body | gsub("\n"; " ") | .[:100])"'
```

Without `gh`, read the comments on the issue's web page.

Look for a comment like "I'm working on this" or "Can I take this?". People often say
this and then never open a pull request, so a claim does not last forever:

- The claim is **active** if the person who made it did something in the last 15 days: a
  comment on the issue, or a commit or pull request for it. Do not work on the issue.
- The claim is **expired** if that person has done nothing for 15 days or more. You may
  work on the issue. Say in your pull request description that the issue was claimed by
  `@<their login>` on `<date>`, with no activity since.

### Cover every new line and branch

New and changed code in `astroid/` must be fully covered by tests: every line, and both
sides of every branch (`if`/`else`, early `return`, `and`/`or` short-circuit used as a
guard). Codecov requires 100% patch coverage. A guard that no test ever takes is either
dead code to remove or a missing test case to add.

Check it locally on the tests you touched:

```shell
pytest --cov --cov-branch --cov-report=term-missing tests/<test file>.py -k "<test name>"
```

Each new or changed line in the diff should be absent from the `Missing` column, and no
branch involving it should be listed as partial.
