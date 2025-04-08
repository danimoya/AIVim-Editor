"""
AIVim Test Example File

This file demonstrates various features of AIVim including:
- Code content that can be analyzed
- Multiple functions for testing AI features
- Sample code to explain, improve, or generate from
"""

import math
import random
from typing import List, Dict, Any, Optional


def calculate_fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using a simple recursive approach.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


def parse_data(data_string: str) -> Dict[str, Any]:
    """
    Parse a string of data into a dictionary.
    
    Args:
        data_string: A string in format "key1=value1;key2=value2"
        
    Returns:
        A dictionary of parsed data
    """
    result = {}
    pairs = data_string.split(';')
    
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key.strip()] = value.strip()
    
    return result


class DataProcessor:
    """A class for processing data collections"""
    
    def __init__(self, data: List[int] = None):
        """
        Initialize with optional data
        
        Args:
            data: Initial data to process
        """
        self.data = data or []
    
    def add_item(self, item: int) -> None:
        """
        Add an item to the data list
        
        Args:
            item: The item to add
        """
        self.data.append(item)
    
    def calculate_statistics(self) -> Dict[str, float]:
        """
        Calculate basic statistics for the current data
        
        Returns:
            Dictionary with statistics
        """
        if not self.data:
            return {"mean": 0, "median": 0, "stdev": 0}
        
        # Mean calculation
        mean = sum(self.data) / len(self.data)
        
        # Median calculation
        sorted_data = sorted(self.data)
        mid = len(sorted_data) // 2
        median = (
            sorted_data[mid] 
            if len(sorted_data) % 2 != 0 
            else (sorted_data[mid-1] + sorted_data[mid]) / 2
        )
        
        # Standard deviation calculation
        variance = sum((x - mean) ** 2 for x in self.data) / len(self.data)
        stdev = math.sqrt(variance)
        
        return {
            "mean": mean,
            "median": median,
            "stdev": stdev
        }


# This function could be improved with AI
def search_items(items, search_term):
    """Search for items matching the search term"""
    results = []
    for item in items:
        if search_term in item:
            results.append(item)
    return results


# This code could be explained with AI
def process_transaction(transaction_data, user_id):
    if not transaction_data or "amount" not in transaction_data:
        return {"status": "error", "message": "Invalid transaction data"}
    
    if transaction_data["amount"] <= 0:
        return {"status": "error", "message": "Amount must be positive"}
    
    # Apply transaction fee
    fee = min(transaction_data["amount"] * 0.025, 10)
    net_amount = transaction_data["amount"] - fee
    
    # Record transaction
    transaction_record = {
        "user_id": user_id,
        "amount": transaction_data["amount"],
        "fee": fee,
        "net_amount": net_amount,
        "timestamp": transaction_data.get("timestamp", "now")
    }
    
    # Normally would save to database here
    
    return {
        "status": "success",
        "transaction": transaction_record
    }


# This area could use code generation via the :generate command
# TODO: Implement a function that sorts a list of dictionaries by a specified key
# The function should:
#  - Take a list of dictionaries and a key name as parameters
#  - Return a new sorted list without modifying the original
#  - Handle missing keys gracefully
#  - Support both ascending and descending sorting
#  - Have proper type hinting


# Main demonstration
if __name__ == "__main__":
    # Sample data
    sample_data = [random.randint(1, 100) for _ in range(20)]
    
    # Instantiate processor
    processor = DataProcessor(sample_data)
    
    # Calculate and print statistics
    stats = processor.calculate_statistics()
    print(f"Statistics for sample data:")
    for key, value in stats.items():
        print(f"  {key}: {value:.2f}")
    
    # Fibonacci example
    n = 10
    fib = calculate_fibonacci(n)
    print(f"\nFibonacci number at position {n}: {fib}")
    
    # Parsing example
    data_str = "name=John Doe;age=30;occupation=Developer"
    parsed = parse_data(data_str)
    print("\nParsed data:")
    for key, value in parsed.items():
        print(f"  {key}: {value}")
    
    # Searching example
    items = ["apple", "banana", "orange", "grapefruit", "applesauce"]
    search_results = search_items(items, "apple")
    print(f"\nSearch results for 'apple': {search_results}")
    
    # Transaction example
    transaction = {
        "amount": 100.00,
        "description": "Test payment",
        "timestamp": "2023-04-01T12:30:45"
    }
    result = process_transaction(transaction, "user123")
    print("\nTransaction result:")
    for key, value in result.items():
        print(f"  {key}: {value}")