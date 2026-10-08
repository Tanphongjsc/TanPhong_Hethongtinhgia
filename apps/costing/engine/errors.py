class CostingError(Exception):
    def __init__(self, message, *, code="CONFIGURATION_ERROR", stage="configuration"):
        super().__init__(message)
        self.code = code
        self.stage = stage
