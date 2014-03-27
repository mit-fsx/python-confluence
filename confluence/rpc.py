import logging
import posixpath
import re
import sys
import urlparse
import warnings
import xmlrpclib

from functools import wraps
from .types import *

def autorenew(f):
    @wraps(f)
    def autorenew(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except InvalidSessionException:
            self._reconnect()
            return f(self, *args, **kwargs)
    return autorenew

class ConfluenceError(Exception):
    rpc_exception = re.compile(
        r'java.lang.Exception: com.atlassian.confluence.rpc.(\w+): (.*)$')

    def __init__(self, msg, fault=None):
        super(ConfluenceError, self).__init__(msg)
        self.fault = fault

    @staticmethod
    def from_fault(fault):
        print fault.faultString
        if fault.faultString.startswith('java.lang.NoSuchMethodException'):
            return ConfluenceError('No such method')
        match = ConfluenceError.rpc_exception.match(fault.faultString)
        cls = ConfluenceError
        msg = fault.faultString
        if match is not None:
            try:
                cls = getattr(sys.modules[__name__], match.group(1))
                msg = match.group(2)
            except AttributeError:
                msg = 'No Exception class found for "{0}"'.format(msg)
        return cls(msg, fault)

class InvalidSessionException(ConfluenceError):
    pass

class RemoteException(ConfluenceError):
    pass

class AuthenticationFailedException(ConfluenceError):
    pass

class NotPermittedException(ConfluenceError):
    pass

class Session:
    def __init__(self, host, **kwargs):
        self._host = host
        self._ssl = kwargs.get('ssl', True)
        self._path = kwargs.get('path', '/confluence/rpc/xmlrpc')
        self._auto_renew = kwargs.get('auto_renew', False)
        self._username = None
        self._password = None
        self._client = xmlrpclib.ServerProxy(
            urlparse.urlunsplit((
                    'https' if self._ssl else 'http',
                    self._host,
                    self._path,
                    None,
                    None)),
            verbose=kwargs.get('debug_xmlrpclib', False),
            use_datetime=True)
        self._token = None
        self.logger = logging.getLogger('confluence.session')
        self._server_info = None

    def do(self, method, *margs, **kwargs):
        self.logger.debug('Calling {0}({1})'.format(method, margs))
        args = list(margs)
        if kwargs.get('auth', True):
            if self._token is None:
                raise ConfluenceError("Not logged in.")
            args.insert(0, self._token)
        try:
            return getattr(self._client.confluence1, method)(*args)
        except xmlrpclib.Fault as fault:
            raise ConfluenceError.from_fault(fault)

    def _login(self):
        self.logger.debug("Logging in as {0}".format(self._user))
        self._token = self.do('login', self._user, self._password, auth=False)
        self.logger.debug("Received token: {0}".format(self._token))

    def _reconnect(self):
        self.logger.debug("Attempting to reconnect...")
        self._login()

    def login(self, user, password):
        self._user = user
        self._password = password
        self._login()

    def logout(self):
        rv = self.do('logout')
        if rv:
            self._token = None
        return rv

    @property
    def server_info(self):
        if self._server_info is None:
            self._server_info = self.getServerInfo()
        return self._server_info

    @property
    def base_url(self):
        return self.server_info.baseUrl
    
    @autorenew
    def getServerInfo(self):
        return ServerInfo(self.do('getServerInfo'))

    @autorenew
    def getSpaces(self):
        return [SpaceSummary(x) for x in self.do('getSpaces')]

    @autorenew
    def _getPage(self, *args):
        return Page(self.do('getPage', *args))
    
    def getPageById(self, page_id):
        # This is secretly a String, despite what the API says.
        return self._getPage(str(int(page_id)))

    def getPageByTitle(self, space_key, page_title):
        return self._getPage(space_key, page_title)

    @autorenew
    def renderContent(self, **kwargs):
        space_key = kwargs.get('space_key', '')
        page_id = kwargs.get('page_id', '')
        content = kwargs.get('content', '')
        parameters = kwargs.get('parameters', {})
        style = kwargs.get('style', None)
        if style is not None:
            if 'style' in parameters:
                raise ValueError("Cannot specify 'style' as both a keyword "
                                 "argument and in 'parameters'")
            parameters['style'] = style
        rendered = self.do('renderContent',
                           space_key, page_id, content, parameters)
        return rendered

    @autorenew
    def getLabelsById(self, content_id):
        content_id = confluence_long(content_id)
        return [Label(x) for x in self.do('getLabelsById', content_id)]

    @autorenew
    def getLabelContentById(self, label_id):
        # These are secretly SearchResults.  Thanks, Confluence!
        return [SearchResult(x) for x in self.do('getLabelContentById',
                                                 confluence_long(label_id))]

    @autorenew
    def getLabelContentByName(self, label_name):
        # These are secretly SearchResults.  Thanks, Confluence!
        return [SearchResult(x) for x in self.do('getLabelContentByName',
                                                 label_name)]

    @autorenew
    def getLabelsByDetail(self, **kwargs):
        label_name = kwargs.get('label_name', '')
        namespace = kwargs.get('namespace', '')
        space_key = kwargs.get('space_key', '')
        owner = kwargs.get('owner', '')
        return [Label(x) for x in 
                self.do('getLabelsByDetail', label_name, namespace,
                        space_key, owner)]

    @autorenew
    def addLabelByName(self, label_name, object_id):
        return self.do('addLabelByName', label_name, confluence_long(object_id))

    def make_short_url(self, shortcode):
        # Doing this with urlparse is harder than it needs to be, since
        # the baseurl contains a location and component, whereas we really
        # just want to concatenate and dedup any slashes
        # This is _slightly_ better than abusing str.format
        # and str.strip(), but not by much
        return posixpath.join(self.base_url, 'x', shortcode)
