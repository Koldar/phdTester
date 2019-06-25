class ValueToIgnoreError(Exception):
    """
    Exception to raise if we can't accept a generated error
    """
    pass


class ResourceNotFoundError(Exception):
    pass


class ResourceTypeUnhandledError(Exception):
    pass


class OptionConversionError(Exception):
    """
    Exception to generate when we can't convert an option in IOptionType
    """
    pass


class UncompliantTestContextError(Exception):
    """
    Thrown when a ITestContext is not compliant with the option graph
    """
    pass


class IgnoreCSVRowError(Exception):
    """
    Exception to raise if a line of the csv needs to be skipped
    """
    pass


class ExternalProgramFailureError(Exception):

    def __init__(self, exit_code: int, cwd: str, program: str):
        self.exit_code = exit_code
        self.cwd = cwd
        self.program = program

    def __str__(self):
        return f"""
        CWD= {self.cwd}
        PROGRAM = {self.program}
        EXIT CODE = {self.exit_code}
        """
