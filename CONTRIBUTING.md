# Contributing to ADgents

Thank you for your interest in contributing to ADgents! This guide will help you get started.

## Code of Conduct

We're committed to providing a welcoming and inclusive environment. Please treat all contributors with respect.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- pip or Poetry
- Git
- A code editor (VS Code recommended)

### Development Setup

1. **Clone the repository:**
```bash
git clone https://github.com/CYBERBULL123/ADgents.git
cd ADgents
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode:**
```bash
pip install -e ".[dev]"
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. **Run tests:**
```bash
pytest tests/ -v
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/bug-description
```

### 2. Make Your Changes

Follow the code style guidelines below.

### 3. Write Tests

Add tests for new functionality:

```python
# tests/test_your_feature.py
import pytest
from core.your_module import YourClass

def test_your_feature():
    obj = YourClass()
    result = obj.your_method()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_feature():
    obj = YourClass()
    result = await obj.async_method()
    assert result is not None
```

### 4. Update Documentation

- Add docstrings to new functions/classes
- Update relevant documentation files in `docs/`
- Add examples if adding new functionality

### 5. Run Tests and Linting

```bash
# Run tests
pytest tests/ -v --cov=core

# Check code style
flake8 core/ server.py
black --check core/ server.py
isort --check-only core/ server.py

# Fix formatting issues
black core/ server.py
isort core/ server.py
```

### 6. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature" -m "Description of changes"
```

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style Guide

### Python Style

We follow PEP 8 with some additions:

**Naming Conventions:**
- Classes: `PascalCase` (e.g., `MyClass`)
- Functions/variables: `snake_case` (e.g., `my_function`)
- Constants: `UPPER_CASE` (e.g., `MAX_AGENTS`)
- Private methods: `_leading_underscore` (e.g., `_internal_method`)

**Line Length:** Maximum 100 characters

**Imports:** Organize in this order:
```python
# Standard library
import os
import json
from datetime import datetime

# Third-party
import httpx
import pytest

# Local
from core.agent import Agent
from core.persona import Persona
```

**Docstrings:** Use Google-style docstrings:
```python
def my_function(param1: str, param2: int) -> str:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: Description of when raised.
    
    Example:
        >>> result = my_function("test", 42)
        >>> print(result)
        "test-42"
    """
    pass
```

### File Organization

```
module/
├── __init__.py
├── core_file.py          # Main implementation
├── utils.py              # Utilities
└── exceptions.py         # Custom exceptions
```

## Testing Guidelines

### Test Structure

```python
import pytest
from core.module import MyClass

class TestMyClass:
    """Tests for MyClass."""
    
    @pytest.fixture
    def instance(self):
        """Create a test instance."""
        return MyClass()
    
    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        result = instance.method()
        assert result is not None
    
    def test_error_handling(self, instance):
        """Test error handling."""
        with pytest.raises(ValueError):
            instance.invalid_method()
    
    @pytest.mark.asyncio
    async def test_async_method(self, instance):
        """Test async methods."""
        result = await instance.async_method()
        assert result == expected
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agent.py

# Run specific test
pytest tests/test_agent.py::TestAgent::test_init

# Run with coverage
pytest --cov=core tests/

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Test Coverage

Aim for at least 80% code coverage:

```bash
pytest --cov=core --cov-report=html tests/
# View coverage at htmlcov/index.html
```

## Adding New Features

### 1. Adding a New Skill

```python
# core/skills.py
from core.skills import register_skill

@register_skill(
    name="my_skill",
    description="What the skill does",
    parameters={
        "param1": "Description",
        "param2": "Description"
    }
)
def my_skill(param1: str, param2: int) -> str:
    """Implementation."""
    return result
```

### 2. Adding a New LLM Provider

```python
# core/llm.py
class MyLLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def generate(self, prompt: str) -> str:
        # Implementation
        pass
    
    def supports_streaming(self) -> bool:
        return True
```

### 3. Adding a New Agent Template

```python
# core/persona.py
PERSONA_TEMPLATES = {
    "my_agent": Persona(
        name="My Agent",
        role="Role",
        expertise_domains=["Domain1", "Domain2"],
        # ... other attributes
    )
}
```

## Documentation Contributions

We welcome documentation improvements!

### Updating Documentation

1. Edit the relevant file in `docs/`
2. Use Markdown with code examples
3. Keep examples concise and runnable
4. Update the table of contents if adding new sections

### Documentation Standards

- Use clear, concise language
- Include code examples for each major concept
- Add cross-references to related topics
- Keep technical accuracy high
- Test all code examples

## Reporting Issues

### Bug Reports

Provide:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python version, etc.)
- Error traceback if applicable
- Minimal code example

### Feature Requests

Include:
- Clear description of the feature
- Why it would be useful
- Possible implementation approach
- Examples of use cases

## Pull Request Process

### Before Submitting

- [ ] Tests are passing: `pytest tests/ -v`
- [ ] Code is formatted: `black core/ && isort core/`
- [ ] Linting passes: `flake8 core/`
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Description
What does this PR do?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Code follows style guidelines

## Related Issues
Closes #123
```

## Review Process

1. **Automated checks:** All PR checks must pass
2. **Code review:** At least one maintainer reviews the code
3. **Tests:** All tests must pass
4. **Documentation:** Documentation must be clear and accurate
5. **Merge:** Approved PRs are merged to main

## Performance Considerations

When adding features, consider:

- **Memory usage:** Don't create large unnecessary objects
- **API calls:** Batch when possible, use caching
- **Database queries:** Use indices, avoid N+1 queries
- **Concurrency:** Use async/await for I/O operations

## Security Considerations

- **Input validation:** Always validate user input
- **API keys:** Never commit keys, use environment variables
- **SQL injection:** Use parameterized queries
- **XSS protection:** Sanitize user input in web UI
- **Dependencies:** Keep dependencies up to date

## Release Process

We follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

### Steps to Release

1. Update version in `pyproject.toml` and `__init__.py`
2. Update `CHANGELOG.md`
3. Create a git tag: `git tag v1.2.3`
4. Push tag: `git push origin v1.2.3`
5. Create release on GitHub
6. Build and publish: `python -m build && twine upload dist/*`

## Getting Help

- **Questions:** Open a discussion on GitHub
- **Bugs:** Open an issue with detailed information
- **Chat:** Join our Discord community (link in README)
- **Email:** contact us at dev@adgents.io

## Recognition

We appreciate all contributions! Contributors will be:
- Added to CONTRIBUTORS.md
- Credited in release notes
- Mentioned in project announcements

## Additional Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Git Commit Message Best Practices](https://www.conventionalcommits.org/)

---

Thank you for contributing to ADgents! Your efforts help make AI agents more accessible and powerful for everyone.
