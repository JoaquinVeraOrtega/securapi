from typing import Callable, Dict, List
import re

class Endpoint:
    handler: Callable
    method: str
    path: str
    params: Dict
    required_params: List

    def __init__(self, handler: Callable, argspecs, method: str = "GET", path: str = "/") -> None:
        self.handler = handler
        self.method = method
        self.path = path
        self.params = {}
        self.required_params = []
        if argspecs.args:
            self.map_params(argspecs)
        print(self.required_params)
    
    def map_params(self, argspecs):
        number_of_params = len(argspecs.args)
        required_params = number_of_params - len(argspecs.defaults)
        index = 0
        if required_params > 0:
            req_left = required_params
            while req_left != 0:
                self.params[argspecs.args[index]] = ""
                self.required_params.append(argspecs.args[index])
                index += 1
                req_left -= 1
        while index != number_of_params:
            self.params[argspecs.args[index]] = argspecs.defaults[index - required_params]
            index += 1
        
    def update_params(self, q_params: str):
        if not q_params:
            if self.required_params:
                return False
            return self.params
        separated = re.split(r"=|&",q_params)
        index = 0
        new_params = self.params.copy()
        try:
            requireds_recieved = len(self.required_params)
            while index < len(separated):
                new_params[separated[index]] = separated[index + 1]
                if separated[index] in self.required_params:
                    requireds_recieved -= 1
                index += 2
        except Exception as e:
            print(f"Error: {e}")
            return False
        if requireds_recieved > 0:
            return False
        return new_params