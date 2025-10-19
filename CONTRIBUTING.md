# Contributing to AgentEval

Thank you for your interest in contributing to AgentEval! This document provides guidelines and
instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Virtual environment (recommended)

### Initial Setup

1. Clone the repository:

```bash
git clone https://github.com/issacj-17/AgentEval.git
cd AgentEval
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Run the development setup script:

```bash
./setup-dev.sh
```

This script will:

- Install all development dependencies
- Set up pre-commit hooks
- Configure git hooks for quality checks
- Optionally run initial checks on all files

Alternatively, you can set up manually:

```bash
pip install -e ".[dev]"
make install-hooks
```

## Development Workflow

### Code Quality Tools

We use several tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter (replaces Black, isort, flake8, bandit)
- **mypy**: Static type checking
- **mdformat**: Markdown formatting
- **pytest**: Testing framework

### Quick Commands

Use the Makefile for common tasks:

```bash
make help              # Show all available commands
make format            # Auto-format code with black and isort
make lint              # Run all linting checks
make type-check        # Run type checking
make security-check    # Run security scanning
make test              # Run tests with coverage
make test-unit         # Run only unit tests
make test-integration  # Run only integration tests
make test-all          # Run all checks and tests
make clean             # Clean generated files
```

## Pre-commit Hooks

Pre-commit hooks automatically run when you commit code. They check:

1. **File checks**: Trailing whitespace, end-of-file fixes, YAML/JSON validity
1. **Code formatting**: Ruff format
1. **Linting**: Ruff linter (includes security checks from bandit rules)
1. **Type checking**: Mypy (excluding tests)
1. **Markdown formatting**: mdformat with GitHub Flavored Markdown support
1. **Tests**: Unit tests run on pre-push

### Running Hooks Manually

Run all pre-commit hooks on staged files:

```bash
pre-commit run
```

Run all hooks on all files:

```bash
pre-commit run --all-files
```

Run a specific hook:

```bash
pre-commit run ruff
pre-commit run ruff-format
pre-commit run mypy
pre-commit run mdformat
```

### Skipping Hooks (Not Recommended)

In rare cases, you may need to skip hooks:

```bash
git commit --no-verify -m "Your commit message"
```

**Warning**: Only skip hooks if absolutely necessary and ensure your code passes all checks before
pushing.

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semi-colons, etc.)
- **refactor**: Code refactoring without feature changes
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **build**: Build system or dependency changes
- **ci**: CI/CD configuration changes
- **chore**: Other changes that don't modify src or test files

### Examples

```bash
feat(agents): add persona agent with memory tracking

Add PersonaAgent class that simulates user behavior with
state persistence across conversation turns.

Closes #123
```

```bash
fix(api): correct rate limiting middleware calculation

The rate limit was incorrectly calculated for burst traffic.
Updated to use sliding window algorithm.
```

```bash
test(integration): add campaign orchestration tests

Add comprehensive integration tests for the campaign
lifecycle including agent coordination.
```

## Testing

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test suites
make test-unit
make test-integration
make test-e2e

# Run specific test file
pytest tests/unit/test_agents.py -v

# Run specific test function
pytest tests/unit/test_agents.py::test_persona_agent_init -v
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Place end-to-end tests in `tests/e2e/`
- Use pytest fixtures for common setup (see `tests/conftest.py`)
- Mock AWS services using pytest-mock
- Aim for high test coverage (>80%)

### Test Guidelines

1. **Unit tests**: Test individual functions/classes in isolation
1. **Integration tests**: Test interactions between components
1. **E2E tests**: Test complete workflows from start to finish
1. Use descriptive test names: `test_<what>_<condition>_<expected_result>`
1. Follow AAA pattern: Arrange, Act, Assert

## Code Style Guidelines

### Python Style

- Follow PEP 8 with line length of 100
- Use type hints for all function signatures
- Write docstrings for public functions/classes (Google style)
- Use meaningful variable names
- Keep functions focused and small

### Example

```python
from typing import Optional

def create_persona_agent(
    persona_id: str,
    config: dict,
    memory: Optional[PersonaMemory] = None
) -> PersonaAgent:
    """Create a persona agent with the specified configuration.

    Args:
        persona_id: Unique identifier for the persona
        config: Configuration dictionary for the agent
        memory: Optional memory instance for state persistence

    Returns:
        Configured PersonaAgent instance

    Raises:
        ValueError: If persona_id is invalid
    """
    # Implementation
    pass
```

## Pull Request Process

1. **Create a feature branch**:

   ```bash
   git checkout -b feat/your-feature-name
   ```

1. **Make your changes**:

   - Write code following style guidelines
   - Add/update tests
   - Update documentation

1. **Run all checks**:

   ```bash
   make test-all
   ```

1. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

1. **Push to your fork**:

   ```bash
   git push origin feat/your-feature-name
   ```

1. **Create a Pull Request**:

   - Use a descriptive title following conventional commits
   - Fill out the PR template
   - Link related issues
   - Ensure all CI checks pass

### PR Review Process

- At least one approval required
- All CI checks must pass
- Code coverage should not decrease
- Documentation must be updated

## Project Structure

```
agenteval/
├── src/agenteval/          # Main source code
│   ├── agents/             # Agent implementations
│   ├── api/                # FastAPI routes and middleware
│   ├── application/        # Business logic services
│   ├── aws/                # AWS service clients
│   ├── evaluation/         # Evaluation metrics
│   ├── factories/          # Factory patterns
│   ├── orchestration/      # Campaign orchestration
│   ├── observability/      # Tracing and monitoring
│   └── reporting/          # Report generation
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── docs/                   # Documentation
├── scripts/                # Operational scripts
└── examples/               # Usage examples
```

## Getting Help

- Check existing issues: https://github.com/issacj-17/AgentEval/issues
- Read the documentation in `/docs`
- Ask questions in discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
