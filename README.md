
# GitHub PR Analyzer

## Description

This project is a GitHub Pull Request (PR) Analyzer that helps developers and teams gain insights into their pull requests. It fetches data from GitHub's API for a specified PR and provides useful information and metrics.

## Features

- Fetches PR data using GitHub API
- Analyzes PR content and metadata
- Provides insights on PR size, complexity, and potential issues
- Generates a summary report for easy review

## Prerequisites

Before running this project, make sure you have the following installed:
- Python 3.7+
- Poetry (for dependency management)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/github-pr-analyzer.git
   cd github-pr-analyzer
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

3. Set up your GitHub API token:
   - Create a GitHub Personal Access Token with the necessary permissions
   - Set the token as an environment variable:
     ```
     export GITHUB_TOKEN=your_token_here
     ```

## Usage

To analyze a Pull Request, run the following command:

```
poetry run python main.py PR-ID
```