class NotFound(Exception):
    def __init__(self, message="NotFound"):
        self.message = message
