# Introduction to Python Programming

## Chapter 1: Getting Started with Python

Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991.

### 1.1 Installing Python

To install Python, download the latest version from python.org. Choose the version appropriate for your operating system.

### 1.2 Your First Python Program

The classic first program in any language is "Hello, World!" In Python, it's simply:

```python
print("Hello, World!")
```

## Chapter 2: Variables and Data Types

### 2.1 Variables

Variables are containers for storing data values. In Python, you don't need to declare the type:

```python
name = "Alice"
age = 25
```

### 2.2 Basic Data Types

Python supports several data types:
- **int**: Whole numbers like 1, 42, -10
- **float**: Decimal numbers like 3.14, -0.5
- **str**: Text like "hello"
- **bool**: True or False

## Chapter 3: Control Flow

### 3.1 If Statements

Control the flow of your program with conditional statements:

```python
if age >= 18:
    print("Adult")
else:
    print("Minor")
```

### 3.2 Loops

Repeat actions with loops:

```python
for i in range(5):
    print(i)
```

## Chapter 4: Functions

### 4.1 Defining Functions

Functions are reusable blocks of code:

```python
def greet(name):
    return f"Hello, {name}!"
```

### 4.2 Function Parameters

Functions can accept multiple parameters:

```python
def add(a, b):
    return a + b
```