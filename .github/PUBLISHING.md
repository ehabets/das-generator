# GitHub Actions Setup Instructions

This repository includes two GitHub Actions workflows:

## 1. Tests Workflow (`tests.yml`)
Runs automatically on:
- Pushes to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

Tests the package on Python 3.11 and 3.12.

## 2. PyPI Publishing Workflow (`publish-to-pypi.yml`)
Publishes to PyPI automatically when you:
- Create a GitHub release
- Push a tag starting with `v` (e.g., `v0.1.0`)

### Setting up PyPI Trusted Publishing

This workflow uses PyPI's **Trusted Publishing** (no API tokens needed!). To set it up:

1. Go to [PyPI](https://pypi.org) and log in
2. Go to your account settings → [Publishing](https://pypi.org/manage/account/publishing/)
3. Add a new "pending publisher" with these details:
   - **PyPI Project Name**: `das-generator`
   - **Owner**: `ehabets`
   - **Repository name**: `das-generator`
   - **Workflow name**: `publish-to-pypi.yml`
   - **Environment name**: (leave empty)

4. The first time you publish, PyPI will create the project automatically

### How to Publish a New Release

#### Option 1: Using GitHub Releases (Recommended)
1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. Create a new tag (e.g., `v0.1.0`)
4. Write release notes
5. Click "Publish release"
6. GitHub Actions will automatically build and publish to PyPI

#### Option 2: Using Git Tags
```bash
# Create and push a tag
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

The workflow will automatically:
- Checkout your code with full git history (for setuptools-scm)
- Build the package
- Validate the distribution
- Publish to PyPI using trusted publishing

### Alternative: Using API Token

If you prefer to use an API token instead of trusted publishing:

1. Generate an API token on [PyPI](https://pypi.org/manage/account/token/)
2. Add it as a repository secret named `PYPI_API_TOKEN`
3. Modify the "Publish to PyPI" step in `publish-to-pypi.yml`:
   ```yaml
   - name: Publish to PyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
       skip-existing: true
   ```

### Testing Locally Before Publishing

Before creating a release, you can test the build process locally:

```bash
# Build the package
python -m pip install build twine
python -m build

# Check the distribution
twine check dist/*

# Optional: Upload to Test PyPI first
twine upload --repository testpypi dist/*
```

### Versioning

The package uses `setuptools-scm` for automatic versioning based on git tags:
- Tagged commits (e.g., `v0.1.0`) → `0.1.0`
- Development commits → `0.1.1.dev3+gabc1234`

Always use semantic versioning for your tags: `vMAJOR.MINOR.PATCH`
