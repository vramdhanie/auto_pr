"""Two ways to read a pull request from GitHub.

The preferred route is the `gh` CLI, using whatever credentials it is already
signed in with. That matters for work repositories: an organisation behind SAML
SSO requires a personal access token to be explicitly authorised for it, and
many organisations block fine-grained tokens outright. `gh auth login` goes
through the browser flow those organisations already trust, so there is nothing
to authorise and no secret to keep in a .env file.

A personal access token is kept as a fallback, for CI or anywhere `gh` is not
installed.
"""

import json
import shutil
import subprocess

import requests

GITHUB_API_BASE_URL = 'https://api.github.com'

# The pull request fields worth putting in front of a reviewer. The full API
# response is mostly URLs and would crowd out the diff.
PR_FIELDS = [
    'title', 'author', 'baseRefName', 'headRefName',
    'body', 'changedFiles', 'additions', 'deletions',
]


# Function to check whether the gh CLI is installed and signed in
def gh_is_available():
    if shutil.which('gh') is None:
        return False
    result = subprocess.run(
        ['gh', 'auth', 'status'],
        capture_output=True,
        text=True,
        check=False
    )
    return result.returncode == 0


# Function to report which account gh will act as.
# Worth printing: with more than one account configured, a private work
# repository is only readable by the account that has access to it.
def gh_active_account():
    result = subprocess.run(
        ['gh', 'api', 'user', '--jq', '.login'],
        capture_output=True,
        text=True,
        check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


# Function to run a gh command and return its stdout
def run_gh(arguments):
    result = subprocess.run(
        ['gh'] + arguments,
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(arguments)} failed: "
            f"{result.stderr.strip() or 'no error output'}"
        )
    return result.stdout


# Function to ask gh which repository the current directory belongs to
def gh_current_repo():
    try:
        return run_gh([
            'repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'
        ]).strip()
    except RuntimeError:
        return None


# Function to fetch a pull request through the gh CLI
def fetch_via_gh(repo, number):
    raw = run_gh([
        'pr', 'view', str(number), '--repo', repo, '--json', ','.join(PR_FIELDS)
    ])
    pr = json.loads(raw)
    details = {
        'title': pr.get('title'),
        'author': (pr.get('author') or {}).get('login'),
        'base': pr.get('baseRefName'),
        'head': pr.get('headRefName'),
        'description': pr.get('body'),
        'changed_files': pr.get('changedFiles'),
        'additions': pr.get('additions'),
        'deletions': pr.get('deletions'),
    }
    diff = run_gh(['pr', 'diff', str(number), '--repo', repo])
    return details, diff


# Function to fetch a pull request with a personal access token
def fetch_via_token(repo, number, token):
    pr_url = f'{GITHUB_API_BASE_URL}/repos/{repo}/pulls/{number}'

    response = requests.get(pr_url, headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    })
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch pull request details: "
            f"{response.status_code} {response.text}"
        )
    pr = response.json()
    details = {
        'title': pr.get('title'),
        'author': (pr.get('user') or {}).get('login'),
        'base': (pr.get('base') or {}).get('ref'),
        'head': (pr.get('head') or {}).get('ref'),
        'description': pr.get('body'),
        'changed_files': pr.get('changed_files'),
        'additions': pr.get('additions'),
        'deletions': pr.get('deletions'),
    }

    response = requests.get(pr_url, headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3.diff'  # Specifically request diff format
    })
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch pull request diff: {response.status_code} {response.text}"
        )
    return details, response.text


# Function to fetch a pull request, preferring gh and falling back to a token
def fetch_pull_request(repo, number, token=None):
    if gh_is_available():
        account = gh_active_account()
        if account:
            print(f"Using the gh CLI as {account}.")
        return fetch_via_gh(repo, number)

    if token:
        print("gh is not available; falling back to GITHUB_TOKEN.")
        return fetch_via_token(repo, number, token)

    raise RuntimeError(
        "No way to reach GitHub. Either install the gh CLI and run `gh auth login`, "
        "or set GITHUB_TOKEN in your .env file."
    )


# Function to work out which repository to review in.
# Order of preference: the --repo argument, then REPO_OWNER/REPO_NAME from the
# environment, then whatever repository the current directory belongs to.
def resolve_repo(repo_argument, owner=None, name=None):
    if repo_argument:
        return repo_argument
    if owner and name:
        return f'{owner}/{name}'
    inferred = gh_current_repo() if gh_is_available() else None
    if inferred:
        return inferred
    raise ValueError(
        "Could not work out which repository to use. Pass --repo OWNER/NAME, set "
        "REPO_OWNER and REPO_NAME, or run this from inside a checkout of "
        "the repository."
    )
