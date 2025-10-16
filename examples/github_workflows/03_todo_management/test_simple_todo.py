#!/usr/bin/env python3
"""
Simple test file with a TODO for testing the agent.
"""

def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    # TODO(openhands): add input validation to check if inputs are numbers
    return a + b


def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()