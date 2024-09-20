import requests
from requests.auth import HTTPBasicAuth
import json
import openai
import argparse

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables
BITBUCKET_USERNAME = os.getenv('BITBUCKET_USERNAME')
BITBUCKET_APP_PASSWORD = os.getenv('BITBUCKET_APP_PASSWORD')
WORKSPACE = os.getenv('WORKSPACE')
REPOSITORY_SLUG = os.getenv('REPOSITORY_SLUG')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Validate that all required environment variables are set
required_vars = ['BITBUCKET_USERNAME', 'BITBUCKET_APP_PASSWORD', 'WORKSPACE', 'REPOSITORY_SLUG',  'OPENAI_API_KEY']
for var in required_vars:
    if not locals()[var]:
        raise ValueError(f"Environment variable {var} is not set")

# Base URL for Bitbucket API
BITBUCKET_API_BASE_URL = 'https://api.bitbucket.org/2.0'
PULL_REQUEST_ID = ''

# Update PR_DETAILS_URL and PR_DIFF_URL to use the base URL
PR_DETAILS_URL = f'{BITBUCKET_API_BASE_URL}/repositories/{WORKSPACE}/{REPOSITORY_SLUG}/pullrequests/{PULL_REQUEST_ID}'
PR_DIFF_URL = f'{BITBUCKET_API_BASE_URL}/repositories/{WORKSPACE}/{REPOSITORY_SLUG}/pullrequests/{PULL_REQUEST_ID}/diff'

# Function to fetch pull request details
def get_pull_request_details():
    response = requests.get(PR_DETAILS_URL, auth=HTTPBasicAuth(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))
    if response.status_code == 200:
        pr_details = response.json()
        return pr_details
    else:
        raise Exception(f"Failed to fetch pull request details: {response.status_code} {response.text}")

# Function to fetch pull request diff
def get_pull_request_diff():
    response = requests.get(PR_DIFF_URL, auth=HTTPBasicAuth(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))
    if response.status_code == 200:
        pr_diff = response.text
        return pr_diff
    else:
        raise Exception(f"Failed to fetch pull request diff: {response.status_code} {response.text}")


def get_gpt4_completion(prompt):
    openai.api_key = OPENAI_API_KEY
    system_prompt = """You are an expert code reviewer specializing in React with TypeScript, SCSS, and Redux applications. Your task is to review pull requests and provide constructive feedback. Consider the following best practices:

    1. React with TypeScript:
       - Use functional components and hooks instead of class components
       - Implement proper state management with correct typing
       - Optimize rendering with useMemo and useCallback where appropriate
       - Follow the single responsibility principle for components
       - Utilize TypeScript features like interfaces, types, and generics for better type safety
       - Use proper type annotations for props, state, and function parameters/returns

    2. SCSS:
       - Use variables for consistent theming
       - Implement proper nesting to avoid specificity issues
       - Utilize mixins and functions for reusable styles
       - Follow BEM or a similar naming convention for clarity

    3. Redux with TypeScript:
       - Keep the store as flat as possible
       - Use Redux Toolkit for simplified Redux logic with TypeScript support
       - Implement proper action creators and reducers with correct type definitions
       - Utilize selectors for derived state
       - Define and use proper TypeScript interfaces for your state and actions

    4. General:
       - Ensure code is DRY (Don't Repeat Yourself)
       - Maintain consistent naming conventions
       - Write clear, concise comments and documentation
       - Implement proper error handling with TypeScript's error types
       - Use strict TypeScript configuration for maximum type safety

    Analyze the provided code and suggest improvements in:
    - TypeScript usage and type safety
    - Performance optimization
    - Code organization and structure
    - Adherence to React, TypeScript, SCSS, and Redux best practices
    - Potential bugs or edge cases
    - Readability and maintainability

    Provide specific, actionable feedback with TypeScript code examples where applicable."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=4000  # Increased token limit for more comprehensive reviews
        )
        
        # Extract the response content
        completion = response.choices[0].message.content
        return completion

    except Exception as e:
        return f"Error occurred: {e}"

def main():

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process pull request details.')
    parser.add_argument('pr', type=int, help='The ID of the pull request to process')
    args = parser.parse_args()

    # Update PULL_REQUEST_ID with the command line argument
    global PULL_REQUEST_ID
    PULL_REQUEST_ID = args.pr

    # Update PR_DETAILS_URL and PR_DIFF_URL with the new PULL_REQUEST_ID
    global PR_DETAILS_URL, PR_DIFF_URL
    PR_DETAILS_URL = f'{BITBUCKET_API_BASE_URL}/repositories/{WORKSPACE}/{REPOSITORY_SLUG}/pullrequests/{PULL_REQUEST_ID}'
    PR_DIFF_URL = f'{BITBUCKET_API_BASE_URL}/repositories/{WORKSPACE}/{REPOSITORY_SLUG}/pullrequests/{PULL_REQUEST_ID}/diff'
    try:
        pr_details = get_pull_request_details()
        
        pr_diff = get_pull_request_diff()
    
        # Prepare the user prompt with PR details and diff
        user_prompt = f"""Please review the following pull request details and diff:

Pull Request Details:
{pr_details}

Pull Request Diff:
{pr_diff}

Please provide a comprehensive code review, focusing on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Adherence to TypeScript, React, and Redux standards
5. Suggestions for improvements

Offer specific, actionable feedback with code examples where applicable."""

        print("Generated user prompt for GPT-4 review:")
        print(user_prompt)

        # Get the completion from GPT-4
        gpt4_response = get_gpt4_completion(user_prompt)

        # Print the result
        print("GPT-4 response:")
        print(gpt4_response)
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()