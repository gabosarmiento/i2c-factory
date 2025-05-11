
# Simple calculator module
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
    
# TODO: Add more functions


def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
