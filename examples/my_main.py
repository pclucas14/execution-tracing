from src.tracer.core import Tracer
import numpy as np

def level3_function(value):
    print(f"Inside level3_function with value: {value}")
    xx = np.array([1, 2, 3])
    return xx.sum() * value * 2

def level2_function(x, y):
    print(f"Inside level2_function with x: {x}, y: {y}")
    result = level3_function(x + y)
    return result + 10

def level1_function(name, count=5):
    print(f"Inside level1_function with name: {name}, count: {count}")
    total = 0
    for i in range(count):
        total += level2_function(i, i+1)
    return f"Result for {name}: {total}"

def main():
    level1_function("example", 3)


if __name__ == "__main__":
    main()