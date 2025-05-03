#!/usr/bin/env python3

"""
Test script to fix the NLP mode bug with tuple unpacking
"""

def simulate_issue():
    # This simulates what's in the PyPI package that's causing issues
    print("Testing bug reproduction...")
    nlp_sections = [(1, 2), (3, 4, "query"), (5, 6)]
    comment_start = 3
    
    try:
        # This will cause ValueError: too many values to unpack (expected 2)
        result = any(start <= comment_start <= end for start, end in nlp_sections)
        print(f"Result (should not reach here): {result}")
    except ValueError as e:
        print(f"Error detected: {e}")
    
    # Now fix with the proper approach
    print("\nTesting fixed version...")
    inside_existing_section = False
    for section in nlp_sections:
        # Handle both 2-tuple and 3-tuple formats safely
        if len(section) >= 2:  # Could be 2 or 3 elements
            # Access by index rather than unpacking to avoid ValueError
            section_start = section[0]
            section_end = section[1]
            if section_start <= comment_start <= section_end:
                inside_existing_section = True
                break
                
    print(f"Inside existing section: {inside_existing_section}")

if __name__ == "__main__":
    simulate_issue()
