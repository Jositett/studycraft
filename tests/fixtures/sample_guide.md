# Introduction to Python Programming

## Chapter 1: Variables and Data Types

Python supports several built-in data types including integers, floats, strings, and booleans.

### 1.1 Integers and Floats

Integers are whole numbers like 1, 42, -7. Floats are decimal numbers like 3.14, 2.718.

```python
x = 42
pi = 3.14159
```

### 1.2 Strings

Strings are sequences of characters enclosed in quotes.

```python
name = "Alice"
greeting = f"Hello, {name}!"
```

### 1.3 Booleans

Booleans represent True or False values used in conditional logic.

```python
is_valid = True
has_access = False
```

## Chapter 2: Control Flow

Control flow statements allow you to execute code conditionally or repeatedly.

### 2.1 If Statements

Use if/elif/else to branch logic based on conditions.

```python
age = 18
if age >= 18:
    print("Adult")
elif age >= 13:
    print("Teenager")
else:
    print("Child")
```

### 2.2 For Loops

For loops iterate over sequences like lists, ranges, or strings.

```python
for i in range(5):
    print(i)

fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)
```

### 2.3 While Loops

While loops repeat as long as a condition is true.

```python
count = 0
while count < 5:
    print(count)
    count += 1
```
