class ResumeUploadError(Exception):
    """
    A resume upload was rejected. `code` is stable and machine-readable (the
    frontend maps it to UI copy); `message` is safe to show to the user and never
    contains file contents or internal details.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
