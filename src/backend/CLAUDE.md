# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands
- Install dependencies: `pip install -r requirements.txt`
- Run application: `python app.py`
- Run with Docker: `docker build -t backend . && docker run -p 8000:8000 -e OPENAI_API_KEY=your_api_key backend`

## Testing
- Run tests: `pytest`
- Run single test: `pytest tests/path_to_test.py::test_function_name -v`

## Code Style
- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Sort imports alphabetically: standard library, third-party, local
- Use descriptive variable names (snake_case)
- Handle exceptions explicitly, avoid bare except
- Use f-strings for string formatting
- Docstrings for functions and classes (Google style)
- Maximum line length: 88 characters