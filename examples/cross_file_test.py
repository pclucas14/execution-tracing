from module_for_tracing import function_in_module

def main_function():
    """Main function that calls imported functions."""
    print("Starting cross-file test...")
    result = function_in_module(5)
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main_function()