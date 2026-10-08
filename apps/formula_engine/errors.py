class FormulaError(ValueError):
    """Public domain error with Vietnamese text and source position."""
    def __init__(self, message, *, position=None, category="semantic"):
        self.message = message
        self.position = position
        self.category = category
        super().__init__(message)

    def describe(self, expression=""):
        label = {"syntax": "Lỗi cú pháp", "semantic": "Lỗi nghiệp vụ", "evaluation": "Lỗi kiểm thử"}[self.category]
        if self.position is None:
            return f"{label}: {self.message}"
        before = expression[:self.position]
        line = before.count("\n") + 1
        column = len(before.rsplit("\n", 1)[-1]) + 1
        return f"{label} · Dòng {line}, cột {column}: {self.message}"
