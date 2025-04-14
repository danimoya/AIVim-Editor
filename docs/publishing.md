# Publishing AIVim to PyPI

This document explains how to set up your GitHub repository to automatically publish AIVim to PyPI when you create a new release.

## Prerequisites

1. A PyPI account (register at [pypi.org](https://pypi.org/account/register/))
2. A GitHub repository for AIVim

## Setting Up PyPI API Token

1. Log in to your PyPI account
2. Navigate to Account Settings > API tokens
3. Create a new API token with the scope "Entire account (all projects)"
4. Copy the generated token (you won't be able to see it again!)

## Setting Up GitHub Secret

1. Go to your GitHub repository
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Set the name to `PYPI_API_TOKEN`
5. Paste your PyPI API token as the value
6. Click "Add secret"

## Publishing a New Release

When you're ready to publish a new version of AIVim:

1. Update the version number in `pyproject.toml`
2. Create a new release on GitHub:
   - Click on "Releases" in your repository
   - Click "Create a new release"
   - Set a tag version (e.g., `v0.1.0`)
   - Add release notes
   - Click "Publish release"

The GitHub workflow will automatically:
1. Build the package
2. Upload it to PyPI

## Testing Publishing

If you want to test the publishing process first:

1. Register at [test.pypi.org](https://test.pypi.org/account/register/)
2. Create an API token there
3. Add it as a GitHub secret named `TEST_PYPI_API_TOKEN`
4. Uncomment the `repository-url` line in the workflow file
5. Change the secret name to match your test token

This will publish to TestPyPI instead of the real PyPI.