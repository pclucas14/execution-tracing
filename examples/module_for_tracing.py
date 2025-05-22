def function_in_module(value):
    """A function defined in another module."""
    print(f"Inside function_in_module with value: {value}")
    return helper_in_module(value + 10)

def helper_in_module(num):
    """Helper function in the module."""
    print(f"Inside helper_in_module with num: {num}")
    return num * 2