import time

class RateLimiter:
    def __init__(self, max_per_minute=10):
        self.max_per_minute = max_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        now = time.time()
        self.requests = [r for r in self.requests if now - r < 60]
        
        if len(self.requests) >= self.max_per_minute:
            sleep_time = 60 - (now - self.requests[0])
            print(f"Rate limit reached. Waiting {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
        
        self.requests.append(time.time())
    
    def set_limit(self, new_limit):
        self.max_per_minute = new_limit
        print(f"Rate limit updated to {new_limit} per minute")