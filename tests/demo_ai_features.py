"""
Demonstration script specifically for AIVim's AI-powered features

This script provides a guided demonstration of AIVim's AI features without
requiring user knowledge of Vim or extensive manual interaction.
"""
import os
import sys
import time
import curses
from typing import List, Callable

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import necessary components from AIVim
from main import start_editor
from aivim.ai_service import AIService


def demonstration():
    """
    Run the demonstration in the terminal
    """
    print("AIVim AI Features Demonstration")
    print("===============================")
    print()
    
    # Check if AI services are available
    ai_service = AIService()
    if not ai_service.client:
        print("Error: AI services unavailable.")
        print("Please ensure that:")
        print("  1. The OpenAI package is installed ('pip install openai')")
        print("  2. The OPENAI_API_KEY environment variable is set")
        print()
        print("Exiting demonstration...")
        return
    
    print("This demonstration will show AIVim's AI-powered features:")
    print("  1. Code explanation (:explain)")
    print("  2. Code improvement (:improve)")
    print("  3. Code generation (:generate)")
    print("  4. Custom AI queries (:ai)")
    print()
    print("The demo will open AIVim with our example file and guide you through")
    print("using each feature. You'll need basic familiarity with Vim commands.")
    print()
    print("Press any key to begin the demo...")
    input()
    
    # Run editor using curses wrapper
    example_file = os.path.join(os.path.dirname(__file__), 'example.py')
    print(f"Opening {example_file} in AIVim...")
    print("Use the following commands in the editor:")
    print("  - :explain 110 115    (Explain the search_items function)")
    print("  - :improve 110 115    (Improve the search_items function)")
    print("  - :generate 155 'Sort dictionaries by key'  (Generate code based on TODO)")
    print("  - :ai 'How could I optimize the Fibonacci function?'  (Custom query)")
    print()
    print("Press ESC to exit insert or visual mode")
    print("Use :wq to save and exit the editor")
    print()
    print("Starting editor in 3 seconds...")
    time.sleep(3)
    
    # Use curses wrapper to start the editor
    curses.wrapper(start_editor, example_file)
    
    # Editor has closed
    print()
    print("Demo completed!")
    print("For more information on AIVim features, use the :help command in the editor.")


def explanation_example():
    """
    Example of the explanation feature using direct API calls
    """
    ai_service = AIService()
    
    code = """
def search_items(items, search_term):
    """Search for items matching the search term"""
    results = []
    for item in items:
        if search_term in item:
            results.append(item)
    return results
"""
    
    context = """
# Example usage
items = ["apple", "banana", "orange", "grapefruit", "applesauce"]
search_results = search_items(items, "apple")
print(f"Search results for 'apple': {search_results}")
"""
    
    print("=== Code Explanation Example ===")
    print("Code to explain:")
    print(code)
    print("\nExplanation:")
    explanation = ai_service.get_explanation(code, context)
    print(explanation)
    print()


def improvement_example():
    """
    Example of the improvement feature using direct API calls
    """
    ai_service = AIService()
    
    code = """
def search_items(items, search_term):
    """Search for items matching the search term"""
    results = []
    for item in items:
        if search_term in item:
            results.append(item)
    return results
"""
    
    context = """
# Example usage
items = ["apple", "banana", "orange", "grapefruit", "applesauce"]
search_results = search_items(items, "apple")
print(f"Search results for 'apple': {search_results}")
"""
    
    print("=== Code Improvement Example ===")
    print("Code to improve:")
    print(code)
    print("\nImproved version:")
    improvement = ai_service.get_improvement(code, context)
    print(improvement)
    print()


def generation_example():
    """
    Example of the code generation feature using direct API calls
    """
    ai_service = AIService()
    
    specification = """
# TODO: Implement a function that sorts a list of dictionaries by a specified key
# The function should:
#  - Take a list of dictionaries and a key name as parameters
#  - Return a new sorted list without modifying the original
#  - Handle missing keys gracefully
#  - Support both ascending and descending sorting
#  - Have proper type hinting
"""
    
    context = """
# Example usage:
data = [
    {"name": "John", "age": 30},
    {"name": "Alice", "age": 25},
    {"name": "Bob", "age": 35}
]
sorted_data = sort_dicts_by_key(data, "age")
"""
    
    print("=== Code Generation Example ===")
    print("Specification:")
    print(specification)
    print("\nGenerated code:")
    generated = ai_service.generate_code(specification, context)
    print(generated)
    print()


def custom_query_example():
    """
    Example of custom AI query feature using direct API calls
    """
    ai_service = AIService()
    
    query = "How could I optimize the Fibonacci function for better performance?"
    
    context = """
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
"""
    
    print("=== Custom AI Query Example ===")
    print("Query:")
    print(query)
    print("\nContext:")
    print(context)
    print("\nResponse:")
    response = ai_service.custom_query(query, context)
    print(response)
    print()


def run_api_examples():
    """Run direct API call examples"""
    print("AIVim AI API Examples")
    print("====================")
    
    # Check if AI services are available
    ai_service = AIService()
    if not ai_service.client:
        print("Error: AI services unavailable.")
        print("Please ensure that:")
        print("  1. The OpenAI package is installed ('pip install openai')")
        print("  2. The OPENAI_API_KEY environment variable is set")
        print()
        print("Exiting demonstration...")
        return
    
    print("These examples demonstrate AIVim's AI capabilities using direct API calls.")
    print("This shows how the AI features can be used outside the editor interface.")
    print()
    
    # Run all examples
    examples: List[Callable[[], None]] = [
        explanation_example,
        improvement_example,
        generation_example,
        custom_query_example
    ]
    
    for example in examples:
        example()
        print("Press Enter to continue to the next example...")
        input()
    
    print("Examples completed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--api-examples":
        run_api_examples()
    else:
        demonstration()