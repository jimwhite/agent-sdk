"""Prompt template for TODO implementation."""

PROMPT = """You are an AI assistant helping to implement a TODO comment in a codebase.

TODO Details:
- File: {file_path}
- Line: {line_num}
- Description: {description}

Your task is to:
1. Analyze the TODO comment and understand what needs to be implemented
2. Create a feature branch for this implementation
3. Implement the functionality described in the TODO
4. Create a pull request with your changes

Please make sure to:
- Create a descriptive branch name related to the TODO
- Write clean, well-documented code
- Include appropriate tests if needed
- Create a clear pull request description explaining the implementation

The TODO comment is: {todo_text}

Please implement this TODO and create a pull request with your changes."""