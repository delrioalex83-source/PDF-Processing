"""This program contains functions to validate user input."""

def get_int_range(prompt: str, low: int, high: int) -> int:
    while True: 
        raw = input(prompt)
        try:
            value = int(raw)
        except ValueError:
            print("please enter an integer")
        if value < low or value > high:
            print(f"Please enter an integer between {low} and {high}")
            continue
        return value