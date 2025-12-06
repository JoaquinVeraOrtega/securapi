from typing import Callable, Dict, List
from urllib.parse import parse_qsl

class Endpoint:
    handler: Callable
    method: str
    path: str
    params: Dict
    required_params: List
    request_body: bool = False
    body_required: bool

    def __init__(self, handler: Callable, argspecs, method, body_required, path: str = "/") -> None:
        self.handler = handler
        self.method = method
        self.path = path
        self.params = {}
        self.required_params = []
        self.body_required = body_required
        if argspecs.args:
            self.map_params(argspecs)
    
    def map_params(self, argspecs):
        number_of_params = len(argspecs.args)
        required_params = number_of_params - (len(argspecs.defaults) if argspecs.defaults else 0)
        index = 0
        if required_params > 0:
            req_left = required_params
            while req_left != 0:
                if argspecs.args[index] == "request_body":
                    self.request_body = True

                else:
                    self.params[argspecs.args[index]] = ""
                    self.required_params.append(argspecs.args[index])
                index += 1
                req_left -= 1
        while index != number_of_params:
            if argspecs.args[index] == "request_body":
                self.request_body = True
            else:
                self.params[argspecs.args[index]] = argspecs.defaults[index - required_params]
            index += 1
        
    def update_params(self, q_params: str):
        if not q_params:
            if self.required_params:
                return "Missing required parameters"
            return self.params
        
        try:
            pairs = parse_qsl(q_params, keep_blank_values=True)
            new_params = self.params.copy()
            remaining_required = set(self.required_params)
            
            for key, value in pairs:
                if key not in new_params:
                    raise KeyError(f"{key} is not a valid parameter")
                new_params[key] = value
                remaining_required.discard(key)
            
            if remaining_required:
                return "Missing required parameters"
            return new_params
        except (KeyError, ValueError) as e:
            return str(e)