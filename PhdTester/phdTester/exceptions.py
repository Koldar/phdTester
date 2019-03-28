class ValueToIgnoreError(Exception):
    """
    Exception to raise if we can't accept a generated error
    """
    pass


class ResourceNotFoundError(Exception):
    pass


class ResourceTypeUnhandledError(Exception):
    pass
