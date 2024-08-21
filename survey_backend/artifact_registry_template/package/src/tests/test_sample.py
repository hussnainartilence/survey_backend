"""
This script is used exclusively for testing changes to the package template. Delete from your package.
"""
from ..sample import add, subtract, multiply, divide

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
    assert add(100, -50) == 50

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(10, 5) == 5
    assert subtract(-5, -10) == 5
    assert subtract(0, 0) == 0

def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(0, 10) == 0
    assert multiply(-2, 5) == -10
    assert multiply(2, 0.5) == 1.0

def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(15, 3) == 5.0
    assert divide(5, 2) == 2.5
    assert divide(7, 2) == 3.5 