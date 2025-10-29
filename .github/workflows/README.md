# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD on the `main` branch.

## main-ci-cd.yml

Comprehensive CI/CD pipeline that runs on:

- **Push to main**: Full CI + deployment
- **Pull requests to main**: Full CI only (no deployment)

### Jobs

1. **backend-tests** (Matrix: Python 3.9, 3.10, 3.11)

   - Runs pytest with coverage
   - Uploads coverage to Codecov
   - Uses pip cache for faster builds

2. **backend-quality**

   - Black formatting check
   - Ruff linting
   - MyPy type checking (non-blocking)

3. **frontend-tests**

   - npm build
   - Playwright UI tests (non-blocking)
   - Uploads Playwright reports as artifacts

4. **docker-build**

   - Tests backend Docker image build
   - Tests frontend Docker image build
   - Uses buildx with layer caching

5. **integration-check**

   - Runs integration tests after all other tests pass

6. **deploy** (main branch only)

   - Builds and pushes Docker images
   - Currently configured as placeholder
   - Uncomment Docker Hub steps when ready

7. **ci-success**
   - Final status check
   - Ensures all required jobs passed

### Configuration

The workflow uses these environment variables:

- `PYTHON_VERSION`: "3.9" (primary Python version)
- `NODE_VERSION`: "18" (Node.js version for frontend)

### Secrets Required for Deployment

When ready to enable deployment, add these secrets to your repository:

- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token

### Caching

The workflow uses several caching mechanisms:

- **pip cache**: Caches Python dependencies
- **npm cache**: Caches Node.js dependencies
- **Docker layer cache**: Caches Docker build layers via GitHub Actions cache

### Codecov Integration

Backend test coverage is automatically uploaded to Codecov. Add the `CODECOV_TOKEN` secret if you want private repository support.

### Making Changes

When modifying the workflow:

1. Test changes on a feature branch first
2. Verify all jobs pass before merging to main
3. Update this README if adding/removing jobs

### Local Testing

You can test the workflow locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Run the workflow
act -j backend-tests
act -j frontend-tests
```

### Troubleshooting

**Failing tests on CI but passing locally?**

- Check Python/Node versions match
- Verify dependencies are in requirements.txt/package.json
- Look for environment-specific issues

**Slow builds?**

- Caching should speed up subsequent runs
- First run will be slower as caches are populated

**Docker build failures?**

- Ensure Dockerfile paths are correct
- Check that all required files are in context
- Review build logs in Actions tab
