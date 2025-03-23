import json
import os
from threading import Lock

class CounterService:
    _instance = None
    _lock = Lock()
    ENV_VAR_NAME = 'PDF_CONVERSION_COUNT'
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CounterService, cls).__new__(cls)
            cls._instance._counter_file = 'counter.json'
            # Initialize from environment or file
            cls._instance._initialize_counter()
        return cls._instance
    
    def _initialize_counter(self):
        """Initialize counter from environment or file."""
        try:
            # Try to get count from environment first
            count = int(os.environ.get(self.ENV_VAR_NAME, -1))
            if count < 0:
                # If not in environment, try to get from file
                with open(self._counter_file, 'r') as f:
                    count = json.load(f)["converted_pdf_count"]
                # Store in environment for future use
                os.environ[self.ENV_VAR_NAME] = str(count)
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
            # Initialize counter if no valid count found
            count = 0
            os.environ[self.ENV_VAR_NAME] = str(count)
            self.save_counter(count)
    
    def load_counter(self):
        """Load the current counter value."""
        try:
            return int(os.environ.get(self.ENV_VAR_NAME, 0))
        except ValueError:
            return 0
    
    def save_counter(self, count):
        """Save the counter value to both environment and file."""
        os.environ[self.ENV_VAR_NAME] = str(count)
        # Also save to file as backup
        with open(self._counter_file, 'w') as f:
            json.dump({"converted_pdf_count": count}, f)
    
    def increment(self):
        """Thread-safe increment of the counter."""
        with self._lock:
            count = self.load_counter() + 1
            self.save_counter(count)
            return count
    
    def get_count(self):
        """Get the current counter value."""
        return self.load_counter() 