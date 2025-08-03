# Contributing to Family Tree App

Thank you for your interest in contributing to the Family Tree App! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.8+
- Poetry for dependency management
- Git for version control
- Basic understanding of Django framework

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/danieleschmidt/family_tree_app.git
   cd family_tree_app
   ```

2. **Install dependencies**
   ```bash
   pip install poetry
   poetry install
   poetry shell
   ```

3. **Set up the database**
   ```bash
   python source/manage.py migrate
   python source/manage.py createsuperuser
   ```

4. **Run the development server**
   ```bash
   python source/manage.py runserver
   ```

## How to Contribute

### Reporting Issues

Before creating an issue, please:
- Check if the issue already exists
- Provide a clear and descriptive title
- Include steps to reproduce the problem
- Add relevant screenshots or error messages
- Specify your environment (OS, Python version, browser)

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has been requested before
- Clearly describe the feature and its benefits
- Provide use cases and examples
- Consider implementation complexity

### Code Contributions

#### Branch Naming Convention
- Feature: `feature/your-feature-name`
- Bug fix: `bugfix/issue-description`
- Documentation: `docs/topic-name`
- Refactoring: `refactor/component-name`

#### Pull Request Process

1. **Fork and create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   poetry run pytest
   poetry run flake8 source
   poetry run black source --check
   ```

4. **Commit your changes**
   ```bash
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Commit Message Format

Follow the conventional commits format:
- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding or updating tests
- `perf:` performance improvements

## Coding Standards

### Python Code Style
- Follow PEP 8 guidelines
- Use Black for code formatting
- Use isort for import organization
- Maximum line length: 88 characters
- Use type hints where appropriate

### Django Conventions
- Follow Django's coding style
- Use meaningful model and field names
- Include docstrings for complex functions
- Implement proper error handling
- Use Django's built-in security features

### Frontend Standards
- Use semantic HTML
- Follow Bootstrap conventions
- Ensure responsive design
- Add proper ARIA labels for accessibility
- Test across different browsers

## Testing

### Writing Tests
- Write unit tests for new functionality
- Include integration tests for complex workflows
- Maintain test coverage above 80%
- Use descriptive test names
- Mock external dependencies

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=source --cov-report=html

# Run specific test files
poetry run pytest tests/unit/test_services.py
```

## Documentation

### Code Documentation
- Add docstrings to all public functions and classes
- Document complex algorithms and business logic
- Include type hints for function parameters and returns
- Update API documentation for new endpoints

### User Documentation
- Update README.md for setup changes
- Add feature documentation to docs/guides/
- Include screenshots for UI changes
- Update CHANGELOG.md with significant changes

## Security Guidelines

### Reporting Security Issues
- Do not create public issues for security vulnerabilities
- Email security concerns to [INSERT SECURITY EMAIL]
- Include detailed steps to reproduce the issue
- Allow time for assessment before public disclosure

### Security Best Practices
- Never commit secrets or API keys
- Validate all user inputs
- Use Django's built-in security features
- Follow OWASP security guidelines
- Regular dependency updates

## Community Guidelines

### Communication
- Be respectful and constructive
- Help newcomers get started
- Share knowledge and resources
- Follow the Code of Conduct

### Code Review
- Review code for functionality and style
- Provide constructive feedback
- Be open to feedback on your code
- Focus on the code, not the person

## Release Process

### Version Management
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update CHANGELOG.md with each release
- Tag releases in Git
- Include migration notes for breaking changes

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version number bumped
- [ ] Security audit completed
- [ ] Performance regression testing

## Need Help?

- Check the documentation in docs/
- Look at existing code examples
- Ask questions in discussions
- Join our community chat
- Contact maintainers directly

Thank you for contributing to the Family Tree App! 🌳