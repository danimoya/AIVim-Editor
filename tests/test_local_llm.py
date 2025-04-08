#!/usr/bin/env python3
"""
Test script for the local LLM integration in AIVim
"""
import os
import sys
import curses

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import AIVim components
from aivim.ai_service import AIService

def main():
    """Main test function for local LLM integration"""
    print("Testing local LLM integration in AIVim")
    
    # Create the AI service
    service = AIService()
    
    # Check if local LLM is available
    if not service.set_model("local"):
        print("\nLocal LLM is not available")
        print("Possible reasons:")
        print("1. llama-cpp-python package is not installed")
        print("2. No local LLM model file found")
        print("\nSuggestions:")
        print("- Install llama-cpp-python: pip install llama-cpp-python")
        print("- Download a GGUF model from https://huggingface.co/")
        print("- Place the model in ./models directory")
        print("- Set LLAMA_MODEL_PATH environment variable to the model path")
        return
    
    # Test simple code explanation
    code_to_explain = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""
    
    print("\nTesting code explanation with local LLM...")
    explanation = service.get_explanation(code_to_explain, "")
    print("\nExplanation from local LLM:")
    print("-" * 50)
    print(explanation)
    print("-" * 50)
    
    # Test code improvement
    print("\nTesting code improvement with local LLM...")
    improvement = service.get_improvement(code_to_explain, "")
    print("\nImprovement from local LLM:")
    print("-" * 50)
    print(improvement)
    print("-" * 50)
    
    # Test custom query
    print("\nTesting custom query with local LLM...")
    query = "What are the risks of using recursion for the factorial function?"
    response = service.custom_query(query, code_to_explain)
    print("\nResponse to custom query from local LLM:")
    print("-" * 50)
    print(response)
    print("-" * 50)
    
    print("\nLocal LLM testing complete")

if __name__ == "__main__":
    main()