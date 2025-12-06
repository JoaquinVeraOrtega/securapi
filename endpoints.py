from typing import Callable, Dict, List
import re

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
        separated = re.split(r"=|&",q_params)
        index = 0
        new_params = self.params.copy()
        try:
            requireds_recieved = len(self.required_params)
            while index < len(separated):
                if separated[index] not in new_params:
                    raise KeyError(f"{separated[index]} is not a valid parameter")
                new_params[separated[index]] = separated[index + 1]
                if separated[index] in self.required_params:
                    requireds_recieved -= 1
                index += 2
        except Exception as e:
            return str(e)
        if requireds_recieved > 0:
            return "Missing required parameters"
        return new_params