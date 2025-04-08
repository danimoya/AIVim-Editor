#!/usr/bin/env python3
"""
Example Python file to test AIVim functionality
"""

class Calculator:
    """A simple calculator class for testing"""
    
    def __init__(self):
        """Initialize the calculator"""
        self.result = 0
    
    def add(self, a, b):
        """Add two numbers"""
        return a + b
    
    def subtract(self, a, b):
        """Subtract b from a"""
        return a - b
    
    def multiply(self, a, b):
        """Multiply two numbers"""
        return a * b
    
    def divide(self, a, b):
        """Divide a by b"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


def factorial(n):
    """Calculate the factorial of n"""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n-1)


def main():
    """Main function"""
    calc = Calculator()
    print("Testing calculator:")
    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"10 - 4 = {calc.subtract(10, 4)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"20 / 5 = {calc.divide(20, 5)}")
    
    print("\nTesting factorial:")
    for i in range(6):
        print(f"{i}! = {factorial(i)}")


if __name__ == "__main__":
    main()