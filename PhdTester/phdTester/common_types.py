# TODO use these type instad of str!
KS001Str = str
PathStr = str
DataTypeStr = str
RegexStr = str
"""
A string representing a python3.6 regular expression
"""

class SlottedClass(object):

    __slots__ = ()


class GetSuchInfo(object):
    """
    A class representing the return value of IDataSource.get_suchthat
    """
    __slots__ = ('path', 'name', 'type', 'ks001', 'tc')

    def __init__(self, path: PathStr, name: KS001Str, type: DataTypeStr, ks001: "KS001", tc: "ITestContext"):
        self.path = path
        self.name = name
        self.type = type
        self.ks001 = ks001
        self.tc = tc

    def __iter__(self):
        return (x for x in [self.path, self.name, self.type, self.ks001, self.tc])
