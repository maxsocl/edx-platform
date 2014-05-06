#!/usr/bin/env python
"""
a release-master multitool
"""
from __future__ import print_function, unicode_literals
import sys
from path import path
from git import Repo
from git.refs.symbolic import SymbolicReference
import argparse
from datetime import date, timedelta
from dateutil.parser import parse as parse_datestring
import re
from collections import OrderedDict, defaultdict
import textwrap
import requests
import json
import getpass
try:
    from pygments.console import colorize
except ImportError:
    colorize = lambda color, text: text

JIRA_RE = re.compile(r"\b[A-Z]{2,}-\d+\b")
PR_BRANCH_RE = re.compile(r"remotes/edx/pr/(\d+)")
PROJECT_ROOT = path(__file__).abspath().dirname()
repo = Repo(PROJECT_ROOT)
git = repo.git


def make_parser():
    parser = argparse.ArgumentParser(description="release master multitool")
    parser.add_argument(
        '--previous', '--prev', '-p', metavar="GITREV", default="edx/release",
        help="previous release [%(default)s]")
    parser.add_argument(
        '--current', '--curr', '-c', metavar="GITREV", default="HEAD",
        help="current release candidate [%(default)s]")
    parser.add_argument(
        '--date', '-d',
        help="expected release date: defaults to "
        "next Tuesday [{}]".format(default_release_date()))
    parser.add_argument(
        '--merge', '-m', action="store_true", default=False,
        help="include merge commits")
    parser.add_argument(
        '--table', '-t', action="store_true", default=False,
        help="only print table")
    return parser


def ensure_pr_fetch():
    """
    Make sure that the git repository contains a remote called "edx" that has
    two fetch URLs; one for the main codebase, and one for pull requests.
    Returns True if the environment was modified in any way, False otherwise.
    """
    modified = False
    remotes = git.remote().splitlines()
    if not "edx" in remotes:
        git.remote("add", "edx", "https://github.com/edx/edx-platform.git")
        modified = True
    # it would be nice to use the git-python API to do this, but it doesn't seem
    # to support configurations with more than one value per key. :(
    edx_fetches = git.config("remote.edx.fetch", get_all=True).splitlines()
    pr_fetch = '+refs/pull/*/head:refs/remotes/edx/pr/*'
    if pr_fetch not in edx_fetches:
        git.config("remote.edx.fetch", pr_fetch, add=True)
        git.fetch("edx")
        modified = True
    return modified


def get_github_creds():
    """
    Returns Github credentials if they exist, as a two-tuple of (username, token).
    Otherwise, return None.
    """
    netrc_auth = requests.utils.get_netrc_auth("https://api.github.com")
    if netrc_auth:
        return netrc_auth
    config_file = path("~/.config/edx-release").expand()
    if config_file.isfile():
        with open(config_file) as f:
            config = json.load(f)
        github_creds = config.get("credentials", {}).get("api.github.com", {})
        username = github_creds.get("username", "")
        token = github_creds.get("token", "")
        if username and token:
            return (username, token)
    return None


def ensure_github_creds():
    """
    Make sure that we have Github OAuth credentials. This will check the user's
    .netrc file, as well as the ~/.config/edx-release file. If no credentials
    exist in either place, it will prompt the user to create OAuth credentials,
    and store them in ~/.config/edx-release.

    Returns False if we found credentials, True if we had to create them.
    """
    if get_github_creds():
        return False

    # Looks like we need to create the OAuth creds
    # https://developer.github.com/v3/oauth_authorizations/#create-a-new-authorization
    print("We need to set up OAuth authentication with Github's API. "
          "Your credentials will not be stored.", file=sys.stderr)
    headers = {"User-Agent": "edx-release"}
    payload = {"note": "edx-release"}
    for _ in range(3):  # three tries
        username = raw_input("Github username: ")
        password = getpass.getpass("Github password: ")
        response = requests.post(
            "https://api.github.com/authorizations",
            auth=(username, password),
            headers=headers, data=json.dumps(payload),
        )
        if not response.ok:
            print(
                "Invalid authentication: {}".format(response.json()["message"]),
                file=sys.stderr,
            )
            continue
        else:
            break
    if not response.ok:
        print("Too many invalid authentication attempts.", file=sys.stderr)
        return modified

    # got the token!
    token = response.json()["token"]

    config_file = path("~/.config/edx-release").expand()
    # make sure parent directory exists
    config_file.parent.makedirs_p()
    # read existing config if it exists
    if config_file.isfile():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {}
    # update config
    if not "credentials" in config:
        config["credentials"] = {}
    if not "api.github.com" in config["credentials"]:
        config["credentials"]["api.github.com"] = {}
    config["credentials"]["api.github.com"]["username"] = username
    config["credentials"]["api.github.com"]["token"] = token
    # write it back out
    with open(config_file, "w") as f:
        json.dump(config, f)

    return True


def default_release_date():
    """
    Returns a date object corresponding to the expected date of the next release:
    normally, this Tuesday.
    """
    today = date.today()
    TUESDAY = 2
    days_until_tuesday = (TUESDAY - today.isoweekday()) % 7
    return today + timedelta(days=days_until_tuesday)


def parse_ticket_references(text):
    """
    Given a commit message, return a list of all JIRA ticket references in that
    message. If there are no ticket references, return an empty list.
    """
    return JIRA_RE.findall(text)


class DoesNotExist(Exception):
    def __init__(self, message, commit, branch):
        self.message = message
        self.commit = commit
        self.branch = branch


def get_merge_commit(commit, branch="master"):
    """
    Given a commit that was merged into the given branch, return the merge commit
    for that event.

    http://stackoverflow.com/questions/8475448/find-merge-commit-which-include-a-specific-commit
    """
    commit_range = "{}..{}".format(commit, branch)
    ancestry_paths = git.rev_list(commit_range, ancestry_path=True).splitlines()
    first_parents = git.rev_list(commit_range, first_parent=True).splitlines()
    both = set(ancestry_paths) & set(first_parents)
    for commit_hash in reversed(ancestry_paths):
        if commit_hash in both:
            return repo.commit(commit_hash)
    # no merge commit!
    msg = "No merge commit for {commit} in {branch}!".format(
        commit=commit, branch=branch,
    )
    raise DoesNotExist(msg, commit, branch)


def get_pr_info(num):
    """
    Returns the info from the Github API
    """
    url = "https://api.github.com/repos/edx/edx-platform/pulls/{num}".format(num=num)
    credentials = get_github_creds()
    headers = {
        "Authorization": "token {}".format(credentials[1]),
        "User-Agent": "edx-release",
    }
    response = requests.get(url, headers=headers)
    result = response.json()
    if not response.ok:
        raise requests.exceptions.RequestException(result["message"])
    return result


def get_merged_prs(start_ref, end_ref):
    """
    Return the set of all pull requests (as integers) that were merged between
    the start_ref and end_ref.
    """
    ensure_pr_fetch()
    start_unmerged_branches = set(
        branch.strip() for branch in
        git.branch(all=True, no_merged=start_ref).splitlines()
    )
    end_merged_branches = set(
        branch.strip() for branch in
        git.branch(all=True, merged=end_ref).splitlines()
    )
    merged_between_refs = start_unmerged_branches & end_merged_branches
    merged_prs = set()
    for branch in merged_between_refs:
        match = PR_BRANCH_RE.search(branch)
        if match:
            merged_prs.add(int(match.group(1)))
    return merged_prs


def prs_by_email(start_ref, end_ref):
    """
    Returns an ordered dictionary of {email: pr_list}
    Email is the email address of the person who merged the pull request
    The dictionary is alphabetically ordered by email address
    The pull request list is ordered by merge date
    """
    unordered_data = defaultdict(set)
    for pr_num in get_merged_prs(start_ref, end_ref):
        ref = "refs/remotes/edx/pr/{num}".format(num=pr_num)
        branch = SymbolicReference(repo, ref)
        try:
            merge = get_merge_commit(branch.commit, end_ref)
        except DoesNotExist as err:
            message = (
                "Warning: could not find merge commit for {commit}. "
                "The pull request containing this commit will not be included "
                "in the table.".format(commit=err.commit)
            )
            print(colorize("red", message), file=sys.stderr)
        else:
            unordered_data[merge.author.email].add((pr_num, merge))

    ordered_data = OrderedDict()
    for email in sorted(unordered_data.keys()):
        ordered = sorted(unordered_data[email], key=lambda pair: pair[1].authored_date)
        ordered_data[email] = [num for num, merge in ordered]
    return ordered_data


def generate_table(start_ref, end_ref):
    """
    Return a string corresponding to a commit table to embed in Confluence
    """
    header = "|| Merged By || Author || Title || PR || JIRA || Verified? ||"
    pr_link = "[#{num}|https://github.com/edx/edx-platform/pull/{num}]"
    user_link = "[@{user}|https://github.com/{user}]"
    rows = [header]
    prbe = prs_by_email(start_ref, end_ref)
    for email, pull_requests in prbe.items():
        for i, pull_request in enumerate(pull_requests):
            try:
                pr_info = get_pr_info(pull_request)
                title = pr_info["title"] or ""
                body = pr_info["body"] or ""
                author = pr_info["user"]["login"]
            except requests.exceptions.RequestException as e:
                message = (
                    "Warning: could not fetch data for #{num}: "
                    "{message}".format(num=pull_request, message=e.message)
                )
                print(colorize("red", message), file=sys.stderr)
                title = "?"
                body = "?"
                author = ""
            rows.append("| {merged_by} | {author} | {title} | {pull_request} | {jira} | {verified} |".format(
                merged_by=email if i == 0 else "",
                author=user_link.format(user=author) if author else "",
                title=title.replace("|", "\|"),
                pull_request=pr_link.format(num=pull_request),
                jira=", ".join(parse_ticket_references(body)),
                verified="",
            ))
    return "\n".join(rows)


def generate_email(start_ref, end_ref, release_date=None):
    """
    Returns a string roughly approximating an email.
    """
    if release_date is None:
        release_date = default_release_date()
    prbe = prs_by_email(start_ref, end_ref)

    email = """
        To: {emails}

        You've made changes that are about to be released. All of the commits
        that you either authored or committed are listed below. Please verify them on
        stage.edx.org and stage-edge.edx.org.

        Please record your notes on https://edx-wiki.atlassian.net/wiki/display/ENG/Release+Page%3A+{date}
        and add any bugs found to the Release Candidate Bugs section.

        If you are a non-affiliated open-source contributor to edx-platform,
        the edX employee who merged in your pull request will manually verify
        your change(s), and you may disregard this message.
    """.format(
        emails=", ".join(prbe.keys()),
        date=release_date.isoformat(),
    )
    return textwrap.dedent(email).strip()


def main():
    parser = make_parser()
    args = parser.parse_args()
    if isinstance(args.date, basestring):
        # user passed in a custom date, so we need to parse it
        args.date = parse_datestring(args.date).date()

    ensure_github_creds()

    if args.table:
        print(generate_table(args.previous, args.current))
        return

    print("EMAIL:")
    print(generate_email(args.previous, args.current, release_date=args.date).encode('UTF-8'))
    print("\n")
    print("Wiki Table:")
    print(
        "Type Ctrl+Shift+D on Confluence to embed the following table "
        "in your release wiki page"
    )
    print("\n")
    print(generate_table(args.previous, args.current))

if __name__ == "__main__":
    main()
