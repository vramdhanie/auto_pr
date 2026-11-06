# Auto PR

[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/deps-uv-261230?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Claude Code](https://img.shields.io/badge/reviews-Claude%20Code-D97757?logo=claude&logoColor=white)](https://docs.claude.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Review a GitHub pull request from the command line. It fetches the pull request and its diff, picks a reviewer prompt based on what the diff touches, and sends both to the Claude Code CLI.

**There are no API keys to configure.** Reviews run through your local `claude` install, and GitHub access comes from the `gh` CLI you are already signed in to.

```bash
uv run python main.py 123
```

## Why no tokens

Both halves of this tool borrow credentials you already have:

- **Reviews** go through `claude -p`, using whatever account Claude Code is signed in to.
- **GitHub** access goes through `gh`, using whatever account `gh` is signed in to.

That second point matters for work repositories. An organisation behind SAML SSO requires a personal access token to be explicitly authorised for it, and many organisations block fine-grained tokens outright. `gh auth login` goes through the browser flow those organisations already trust, so there is nothing to authorise and no secret sitting in a `.env` file waiting to expire.

A personal access token is still supported as a fallback, for CI or anywhere `gh` is not installed.

## Setup

**Prerequisites**

| | |
|---|---|
| [uv](https://docs.astral.sh/uv/) | dependency management |
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | installed and signed in — check with `claude --version` |
| [GitHub CLI](https://cli.github.com/) | installed and signed in — check with `gh auth status` |

```bash
git clone https://github.com/vramdhanie/auto_pr.git
cd auto_pr
uv sync
```

That is the whole setup. No `.env` file is required.

## Usage

Run it from inside a checkout of the repository you want to review, and it works out which repository that is:

```bash
uv run python main.py 123
```

Or name the repository explicitly:

```bash
uv run python main.py 123 --repo owner/name
```

### Which account will it use?

`gh` can be signed in to more than one account, and a private repository is only readable by an account with access to it. The tool prints the account it is using before each review:

```
Reviewing pull request #123 in owner/name...
Using the gh CLI as your-username.
```

Switch accounts with `gh auth switch --user <name>`.

### Reviewer profiles

The prompt is assembled from a general reviewer harness plus a section for each kind of code the diff touches. Profiles are detected from the changed file paths, so a full-stack pull request gets both.

| Profile | Triggered by |
|---|---|
| `backend` | `.py` `.pyi` `.sql` `.go` `.rb` `.rs` `.java` `.kt` |
| `frontend` | `.ts` `.tsx` `.js` `.jsx` `.css` `.scss` `.vue` `.svelte` |
| `cpp` | `.c` `.cc` `.cpp` `.cxx` `.h` `.hh` `.hpp` `.hxx` `.cu` `.cuh` |

A diff that touches neither — documentation, configuration — gets the general harness alone.

Override detection when you want to:

```bash
uv run python main.py 123 --profile backend
uv run python main.py 123 --profile backend --profile frontend
```

The prompts live in `prompts.py` and are meant to be edited. Adding a profile means one entry in `PROFILE_BY_EXTENSION` and one in `SECTIONS`.

## Configuration

Everything is optional. Copy `.env.example` to `.env` if you want any of it:

| Variable | Purpose |
|---|---|
| `REPO_OWNER`, `REPO_NAME` | Default repository, if you would rather not pass `--repo` or run from inside a checkout |
| `CLAUDE_MODEL` | Pin a model. Unset uses the Claude Code CLI's default |
| `GITHUB_TOKEN` | Fallback for when `gh` is not available, such as in CI |

## How it works

1. Resolve the repository: `--repo`, then `REPO_OWNER`/`REPO_NAME`, then whatever repository the current directory belongs to.
2. Fetch the pull request metadata and unified diff, through `gh` where available and the REST API otherwise.
3. Detect which reviewer profiles apply from the changed file paths.
4. Assemble the system prompt: general harness plus the matching sections.
5. Pipe the prompt to `claude -p` and print the review.

Diffs longer than 400,000 characters are truncated. Lockfile churn and large refactors otherwise bury the code that actually changed.

## Project layout

```
main.py            entry point: CLI, profile detection, the Claude Code call
prompts.py         reviewer prompts — the general harness and the profiles
pull_requests.py   fetching a pull request, via gh or a token
tests/             tests for profile detection and prompt assembly
```

## Development

```bash
uv sync              # create .venv and install everything
uv run pytest        # run the tests
uv run ruff check .  # lint
```

`ruff check` is clean and is the gate. `ruff format` is deliberately not run: it would rewrite quote style across the whole codebase for no benefit.

`prompts.py` is exempt from the line-length rule. The prompts are prose, and wrapping them at a column limit makes them harder to read without helping the model.

If you need a `requirements.txt` for somewhere that cannot use uv:

```bash
uv export --format requirements-txt > requirements.txt
```

## License

[MIT](LICENSE)
