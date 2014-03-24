class DataObject(object):
    def __init__(self, dct):
        self.__dict__.update(dct)

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__,
                                 repr(self.__dict__))

class SpaceSummary(DataObject):
    pass

class Space(DataObject):
    pass

class PageSummary(DataObject):
    pass

class Page(DataObject):
    pass
