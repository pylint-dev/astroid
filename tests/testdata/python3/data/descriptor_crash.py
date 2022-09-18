import urllib

class Page:
    _urlOpen = staticmethod(urllib.urlopen)

    def getPage(self, url):
        handle = self._urlOpen(url)
        data = handle.read()
        handle.close()
        return data
