import re
from .shortcode import id2code

excerpt_pattern = re.compile('\{excerpt\}(.*?)\{excerpt\}', re.DOTALL)

def confluence_long(long_integer):
    # For the API, 'long' is pronounced java.lang.String
    return str(long(long_integer))

class DataObject(object):
    def __init__(self, dct):
        self.__dict__.update(dct)

    @property
    def confluence_type(self):
        return self.__class__.__name__

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
    @property
    def shortcode(self):
        return id2code(self.id)

    @property
    def excerpt(self):
        content = getattr(self, 'content', None)
        if content is None:
            raise ValueError('Cannot call excerpt() on Page without content')
        excerpt_match = excerpt_pattern.search(self.content)
        if excerpt_match is None:
            return None
        return excerpt_match.group(1).strip()

class Label(DataObject):
    _invalidChars = ':;, .?&[]()#^*@!<>'

    @staticmethod
    def valid_name(label_name):
        return re.search('[{0}]'.format(re.escape(Label._invalidChars)),
                         label_name) is None

class SearchResult(DataObject):
    pass
