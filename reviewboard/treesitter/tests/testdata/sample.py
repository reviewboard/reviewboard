"""Sample Python file for TreeSitter testing."""

import os
import sys
from typing import Optional


def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: The position in the Fibonacci sequence.

    Returns:
        The nth Fibonacci number.
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


class DataProcessor:
    """A class for processing data."""

    def __init__(self, data: Optional[list] = None):
        self.data = data or []
        self.processed = False

    def process(self) -> bool:
        """Process the data."""
        if not self.data:
            return False

        # Process each item
        for i, item in enumerate(self.data):
            if isinstance(item, str):
                self.data[i] = item.upper()
            elif isinstance(item, (int, float)):
                self.data[i] = item * 2

        self.processed = True
        return True

    @property
    def is_processed(self) -> bool:
        """Check if data has been processed."""
        return self.processed


if __name__ == "__main__":
    # Test the functionality
    processor = DataProcessor([1, 2, "hello", 3.14, "world"])

    if processor.process():
        print("Data processed successfully!")
        print(f"Result: {processor.data}")
        print(f"10th Fibonacci: {calculate_fibonacci(10)}")
    else:
        print("Failed to process data")
        sys.exit(1)
