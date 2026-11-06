import argparse
import json
import os
import re
import shutil
import subprocess

from dotenv import load_dotenv

import prompts
import pull_requests

# Load environment variables from .env file
load_dotenv()

# Get environment variables. All of these are optional now: the gh CLI supplies
# the credentials, and can work out the repository from the current directory.
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER')
REPO_NAME = os.getenv('REPO_NAME')

# Optional. Leave unset to use whichever model the Claude Code CLI defaults to.
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL')

# Largest diff we will send for review. Big refactors and lockfile churn can run
# to megabytes, which wastes tokens and buries the code that actually changed.
MAX_DIFF_CHARS = 400_000

# How long to wait for the review before giving up
CLAUDE_TIMEOUT_SECONDS = 600


# Function to work out which reviewer profiles apply, from the paths in the diff.
# A full-stack pull request legitimately matches more than one.
def detect_profiles(pr_diff):
    changed = set(re.findall(r'^\+\+\+ b/(.+)$', pr_diff, re.MULTILINE))
    found = set()
    for path in changed:
        _, _, extension = os.path.basename(path).rpartition('.')
        extension = f'.{extension}' if extension else ''
        for profile, extensions in prompts.PROFILE_BY_EXTENSION.items():
            if extension in extensions:
                found.add(profile)
    return sorted(found)


# Function to build the system prompt: the general harness, plus a section for
# each area the diff actually touches.
def build_system_prompt(profiles):
    sections = [prompts.BASE]
    for profile in profiles:
        sections.append(prompts.SECTIONS[profile])
    return "\n".join(sections)


# Function to keep a very large diff from burying the code that changed
def truncate_diff(pr_diff):
    if len(pr_diff) <= MAX_DIFF_CHARS:
        return pr_diff
    print(f"Diff is {len(pr_diff)} characters; truncating to {MAX_DIFF_CHARS}.")
    return pr_diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated]"


# Function to run the review through the Claude Code CLI.
# Uses the local `claude` install and whatever credentials it is already signed
# in with, so there is no API key to configure or leak.
def get_claude_review(prompt, system_prompt):
    if shutil.which('claude') is None:
        raise RuntimeError(
            "The 'claude' command was not found on PATH. Install Claude Code "
            "and sign in first: https://docs.claude.com/en/docs/claude-code"
        )

    command = ['claude', '-p', '--append-system-prompt', system_prompt]
    if CLAUDE_MODEL:
        command += ['--model', CLAUDE_MODEL]

    try:
        result = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
            check=False
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"claude did not finish within {CLAUDE_TIMEOUT_SECONDS} seconds"
        ) from error

    if result.returncode != 0:
        raise RuntimeError(
            f"claude exited with status {result.returncode}: "
            f"{result.stderr.strip() or 'no error output'}"
        )

    return result.stdout.strip()


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Review a GitHub pull request with Claude Code.'
    )
    parser.add_argument('pr', type=int, help='The number of the pull request to review')
    parser.add_argument(
        '--repo',
        help='Repository as OWNER/NAME. Defaults to REPO_OWNER/REPO_NAME, or the '
             'repository the current directory belongs to.'
    )
    parser.add_argument(
        '--profile',
        action='append',
        choices=sorted(prompts.SECTIONS),
        help='Reviewer profile to apply. Repeatable. '
             'Detected from the diff when not given.'
    )
    args = parser.parse_args()

    try:
        repo = pull_requests.resolve_repo(args.repo, REPO_OWNER, REPO_NAME)

        print(f"Reviewing pull request #{args.pr} in {repo}...")

        pr_details, pr_diff = pull_requests.fetch_pull_request(repo, args.pr, GITHUB_TOKEN)
        pr_diff = truncate_diff(pr_diff)

        profiles = args.profile or detect_profiles(pr_diff)
        if profiles:
            print(f"Reviewer profiles: {', '.join(profiles)}")
        else:
            print(
                "No language-specific profile matched; "
                "using the general reviewer prompt only."
            )

        system_prompt = build_system_prompt(profiles)

        # Prepare the user prompt with PR details and diff
        user_prompt = f"""Please review the following pull request.

Pull Request Details:
{json.dumps(pr_details, indent=2)}

Pull Request Diff:
{pr_diff}
"""

        # Get the review from Claude Code
        review = get_claude_review(user_prompt, system_prompt)

        # Print the result
        print("Review:")
        print(review)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
