# urlimport.py
import sys
import importlib.abc
import types
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

# Debugging
import logging
log = logging.getLogger(__name__)

# Get links from a given URL


def _get_links(url):
    class LinkParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs = dict(attrs)
                links.add(attrs.get('href').rstrip('/'))
            elif tag == 'pack':
                attrs = dict(attrs)
                links.add(attrs.get('hash').rstrip('/'))

    links = set()
    try:
        log.debug('Getting links from %s' % url)
        u = urlopen(url)
        parser = LinkParser()
        parser.feed(u.read().decode('utf-8'))
    except Exception as e:
        log.debug('Could not get links. %s', e)
    log.debug('links: %r', links)
    log.debug(links)
    return links


# 当导入不存在的包时触发
class UrlMetaFinder(importlib.abc.MetaPathFinder):
    def __init__(self, baseurl):
        log.debug(baseurl)
        self._baseurl = baseurl
        self._links = {}
        self._loaders = {baseurl: UrlModuleLoader(baseurl)}

    def find_module(self, fullname, path=None):
        log.debug('find_module: fullname=%r, path=%r', fullname, path)
        if path is None:
            baseurl = self._baseurl
        else:
            if not path[0].startswith(self._baseurl):
                return None
            baseurl = path[0]
        parts = fullname.split('.')
        basename = parts[-1]
        log.debug('find_module: baseurl=%r, basename=%r', baseurl, basename)

        # Check link cache
        if basename not in self._links:
            self._links[baseurl] = _get_links(baseurl)

        # Check if it's a package
        if basename in self._links[baseurl]:
            log.debug('find_module: trying package %r', fullname)
            fullurl = self._baseurl + '/' + basename
            # Attempt to load the package (which accesses __init__.py)
            loader = UrlPackageLoader(fullurl)
            try:
                loader.load_module(fullname)
                self._links[fullurl] = _get_links(fullurl)
                self._loaders[fullurl] = UrlModuleLoader(fullurl)
                log.debug('find_module: package %r loaded', fullname)
            except ImportError as e:
                log.debug('find_module: package failed. %s', e)
                loader = None
            return loader
        # A normal module
        filename = basename + '.py'
        if filename in self._links[baseurl]:
            log.debug('find_module: module %r found', fullname)
            return self._loaders[baseurl]
        else:
            log.debug('find_module: module %r not found', fullname)
            return None

    def invalidate_caches(self):
        log.debug('invalidating link cache')
        self._links.clear()


class KTModuleLoader(importlib.abc.SourceLoader):
    def __init__(self):  # path传进来的
        self._source_cache = {}
        # self._code = code

    def module_repr(self, module):
        return '<urlmodule %r from %r>' % (module.__name__, module.__file__)

    def report(self, info):
        return info
    # Required method

    def load_module(self, m_name):
        code = self.get_code(m_name)
        mod = sys.modules.setdefault(m_name, types.ModuleType(m_name))  # 新建模块
        log.debug(mod)
        mod.__file__ = self.get_filename(m_name)
        mod.__loader__ = self
        mod.__package__ = m_name.rpartition('.')[0]
        # log.debug(_installed_meta_cache)
        # mod.report = self.report
        exec(code, mod.__dict__)
        # importlib.import_module(fullname)
        log.debug(mod)
        return mod

    # Optional extensions
    def get_code(self, m_name):
        src = self.get_source(m_name)
        return compile(src, self.get_filename(m_name),
                       'exec', dont_inherit=True)

    def get_data(self, path):
        pass

    def get_filename(self, m_name):
        return m_name.split('.')[-1] + '.py'

    def get_source(self, m_name):

        filename = self.get_filename(m_name)
        log.debug('loader: reading %r', m_name)
        if filename in self._source_cache:
            log.debug('loader: cached %r', m_name)
            return self._source_cache[m_name]
        try:
            u = urlopen(pathurl+"/"+m_name)
            log.debug(pathurl+"/"+m_name)
            source = u.read().decode('utf-8')
            # source = _get_hashs(pathurl+"/"+m_name)
            log.debug('loader: %r loaded', m_name)
            self._source_cache[m_name] = source
            return source
        except (HTTPError, URLError) as e:
            log.debug('loader: %r failed. %s', m_name, e)
            raise ImportError("Can't load %s" % m_name)

    def is_package(self, m_name):
        return False

# Module Loader for a URL


class UrlModuleLoader(importlib.abc.SourceLoader):
    def __init__(self, baseurl):  # path传进来的
        self._baseurl = baseurl
        self._source_cache = {}

    def module_repr(self, module):
        return '<urlmodule %r from %r>' % (module.__name__, module.__file__)

    # Required method
    def load_module(self, fullname):
        code = self.get_code(fullname)
        mod = sys.modules.setdefault(
            fullname, types.ModuleType(fullname))  # 新建模块
        mod.__file__ = self.get_filename(fullname)
        mod.__loader__ = self
        mod.__package__ = fullname.rpartition('.')[0]
        exec(code, mod.__dict__)
        return mod

    # Optional extensions
    def get_code(self, fullname):
        src = self.get_source(fullname)
        return compile(src, self.get_filename(fullname), 'exec')

    def get_data(self, path):
        pass

    def get_filename(self, fullname):
        return self._baseurl + '/' + fullname.split('.')[-1] + '.py'

    def get_source(self, fullname):
        filename = self.get_filename(fullname)
        log.debug('loader: reading %r', filename)
        if filename in self._source_cache:
            log.debug('loader: cached %r', filename)
            return self._source_cache[filename]
        try:
            u = urlopen(filename)
            # log.debug(filename)
            source = u.read().decode('utf-8')
            log.debug('loader: %r loaded', filename)
            self._source_cache[filename] = source
            return source
        except (HTTPError, URLError) as e:
            log.debug('loader: %r failed. %s', filename, e)
            raise ImportError("Can't load %s" % filename)

    def is_package(self, fullname):
        log.debug("is_package"+fullname)
        return False


# Package loader for a URL
class UrlPackageLoader(UrlModuleLoader):

    def load_module(self, fullname):
        mod = super().load_module(fullname)
        mod.__path__ = [self._baseurl]
        mod.__package__ = fullname

    def get_filename(self, fullname):
        return self._baseurl + '/' + '__init__.py'

    def is_package(self, fullname):
        return True


# Utility functions for installing/uninstalling the loader
_installed_meta_cache = {}


def install_meta(address):
    if address not in _installed_meta_cache:
        finder = UrlMetaFinder(address)
        _installed_meta_cache[address] = finder
        sys.meta_path.append(finder)
        log.debug('%r installed on sys.meta_path', finder)


def remove_meta(address):
    if address in _installed_meta_cache:
        finder = _installed_meta_cache.pop(address)
        sys.meta_path.remove(finder)
        log.debug('%r removed from sys.meta_path', finder)


class UrlPathFinder(importlib.abc.PathEntryFinder):

    def __init__(self, baseurl):  # path传进来的
        self._links = None
        self._loader = UrlModuleLoader(baseurl)  # Loader加载器
        self._baseurl = baseurl

    def find_loader(self, fullname):
        log.debug('find_loader: %r', fullname)
        parts = fullname.split('.')
        basename = parts[-1]
        log.debug(basename)  # 模块名
        # Check link cache
        if self._links is None:
            self._links = []  # See discussion
            self._links = _get_links(self._baseurl)  # 解析远程index目录,返回目录

        # Check if it's a package 整个目录
        if basename in self._links:  # 如果目录里有模块名
            log.debug('find_loader: trying package %r', fullname)
            fullurl = self._baseurl + '/' + basename
            # Attempt to load the package (which accesses __init__.py)
            loader = UrlPackageLoader(fullurl)  # 对象
            try:
                loader.load_module(fullname)  # 加载库，就是import那个不存在的库
                log.debug('find_loader: package %r loaded', fullname)
            except ImportError:
                loader = None
            return (loader, [fullurl])

        # A normal module 单文件模块
        filename = basename + '.py'
        if filename in self._links:
            log.debug('find_loader: module %r found', fullname)
            return (self._loader, [])
        else:
            log.debug('find_loader: module %r not found', fullname)
            return (None, [])

    def invalidate_caches(self):
        log.debug('invalidating link cache')
        self._links = None


# Check path to see if it looks like a URL
_url_path_cache = {}


def handle_url(path):
    log.debug(path)
    if path.startswith(('http://', 'https://')):
        log.debug('Handle path? %s. [Yes]', path)
        if path in _url_path_cache:
            finder = _url_path_cache[path]
        else:
            finder = UrlPathFinder(path)  # 注册finder，path是自己加的远程路径
            _url_path_cache[path] = finder
        return finder
    else:
        log.debug('Handle path? %s. [No]', path)


# 安装钩子，注册handle_url,这样当找不到库时才能触发这里的代码
def install_path_hook():
    sys.path_hooks.append(handle_url)
    log.debug(sys.path_hooks)
    sys.path_importer_cache.clear()
    log.debug('Installing handle_url')


def remove_path_hook():
    sys.path_hooks.remove(handle_url)
    sys.path_importer_cache.clear()
    log.debug('Removing handle_url')


pathurl = 'http://127.0.0.1:8000/'


def main():
    if pathurl not in sys.path:
        sys.path.append(pathurl)
        log.debug(sys.path)
        install_path_hook()


main()

