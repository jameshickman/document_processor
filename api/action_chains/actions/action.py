"""
Base class to define actions that can be activated against the results of a chain macro
"""

class Action:
    def __init__(self, config: dict, fields: dict, results: dict):
        self.config = config
        self.fields = fields
        self.results = results
        pass

    def run(self) -> bool:
        return True

