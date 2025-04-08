#!/usr/bin/env python3
"""
Demo of AIVim's AI features.

This script demonstrates the following AIVim AI capabilities:
1. Code generation
2. Code explanation
3. Code improvement
4. Custom queries
"""
import os


# Function to be later explained by AIVim
def fibonacci(n):
    """Calculate the nth Fibonacci number using a recursive approach."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


# Function to be improved by AIVim
def calculate_primes(max_num):
    """Find all prime numbers up to max_num using a simple approach."""
    primes = []
    for num in range(2, max_num + 1):
        is_prime = True
        for i in range(2, num):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes


# AIVIM GENERATE: Create a function that sorts a list using merge sort
# (The function will be generated here using AIVim's :generate command)


def main():
    """Main function to demonstrate AIVim capabilities."""
    print("Welcome to the AIVim AI Features Demo!")
    print("Open this file in AIVim and try the following commands:")
    print("\n1. Code Explanation:")
    print("   :explain 10 19")
    print("   This will explain the fibonacci function")
    
    print("\n2. Code Improvement:")
    print("   :improve 22 34")
    print("   This will improve the calculate_primes function")
    
    print("\n3. Code Generation:")
    print("   :generate 38 Create a function that sorts a list using merge sort")
    print("   This will generate a merge sort implementation")
    
    print("\n4. Custom Query:")
    print("   :ai What's the difference between the recursive Fibonacci and an iterative implementation?")


if __name__ == "__main__":
    main()