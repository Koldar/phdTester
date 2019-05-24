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
