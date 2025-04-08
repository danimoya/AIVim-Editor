#!/usr/bin/env python3
'''
A simple script with code that could be improved by AI
'''

def calculate_factorial(n):
    '''Calculate the factorial of a number using a recursive approach'''
    # Base case
    if n == 0 or n == 1:
        return 1
    # Recursive case
    else:
        return n * calculate_factorial(n - 1)

def main():
    '''Main function'''
    # Calculate factorial of 5
    result = calculate_factorial(5)
    print("Factorial of 5 is:", result)
    
    # Calculate factorial of 10
    result = calculate_factorial(10)
    print("Factorial of 10 is:", result)
    
    # Calculate factorial of 20 - this might cause issues
    result = calculate_factorial(20)
    print("Factorial of 20 is:", result)

if __name__ == '__main__':
    main()
