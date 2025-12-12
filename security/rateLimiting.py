import time

class RateLimiterMiddleware:
    def __init__(self, max_requests=60, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window # secs
        self.requests = {}
        self.ip_sus = set()


    def new_request_allowed(self, ip_address) -> bool:
        current_time = time.time()
        if ip_address in self.ip_sus:
            self.update_requests(ip_address, current_time)
            return not self.is_ip_suspected(ip_address) 
        

        if ip_address not in self.requests:
            self.requests[ip_address] = []
        
        # Remove timestamps outside the time window
        self.update_requests(ip_address, current_time)

        # Add the current request timestamp
        self.requests[ip_address].append(current_time)
        
        if len(self.requests[ip_address]) > self.max_requests:
            self.ip_sus.add(ip_address)
            return False  # Rate limit exceeded
        return True  # Request allowed
    
    def is_ip_suspected(self, ip_address) -> bool:
        return ip_address in self.ip_sus
    
    def update_requests(self, ip_address, current_time):
        self.requests[ip_address] = [timestamp for timestamp in self.requests[ip_address] if current_time - timestamp < self.time_window]
        if len(self.requests[ip_address]) == 0:
            self.ip_sus.discard(ip_address)

class RateLimitException(Exception):
    pass
        