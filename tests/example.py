#!/usr/bin/env python3
"""
Example file to test AIVim functionality
"""


def calculate_factorial(n):
    """
    Calculate the factorial of a number
    """
    if n < 0:
        return None
    elif n == 0 or n == 1:
        return 1
    else:
        return n * calculate_factorial(n - 1)


def find_fibonacci(n):
    """
    Find the nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b