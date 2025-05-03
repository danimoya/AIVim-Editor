#!/usr/bin/env python3

"""
Testing tuple handling with different structures
"""

def test_tuple_handling():
    """Test different approaches for handling mixed tuple formats"""
    print("Testing tuple handling with different structures...\n")
    
    # Create a list with mixed tuple formats (2-tuple and 3-tuple)
    mixed_tuples = [(1, 2), (3, 4, "query"), (5, 6)]
    comment_start = 3
    
    print("Approach 1: Direct unpacking (will fail)")
    try:
        # This will cause ValueError: too many values to unpack (expected 2)
        result = any(start <= comment_start <= end for start, end in mixed_tuples)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Error detected: {e}")
    
    print("\nApproach 2: Safe access by index")
    inside_existing_section = False
    for section in mixed_tuples:
        # Handle both 2-tuple and 3-tuple formats safely
        if len(section) >= 2:  # Could be 2 or 3 elements
            # Access by index rather than unpacking to avoid ValueError
            section_start = section[0]
            section_end = section[1]
            if section_start <= comment_start <= section_end:
                inside_existing_section = True
                break
                
    print(f"Inside existing section: {inside_existing_section}")
    
    print("\nApproach 3: Type-specific handling")
    inside_existing_section = False
    for section in mixed_tuples:
        if len(section) == 2:
            start, end = section
            if start <= comment_start <= end:
                inside_existing_section = True
                break
        elif len(section) == 3:
            start, end, query = section
            if start <= comment_start <= end:
                inside_existing_section = True
                break
                
    print(f"Inside existing section: {inside_existing_section}")

if __name__ == "__main__":
    test_tuple_handling()
