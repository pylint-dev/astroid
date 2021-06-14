# Copyright (c) 2012-2013 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2015-2016, 2018, 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 Peter Kolbus <peter.kolbus@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE

from astroid import MANAGER, register_module_extender
from astroid.builder import AstroidBuilder


def mechanize_transform():
    return AstroidBuilder(MANAGER).string_build(
        """

class Browser(object):
    def __getattr__(self, name):
        return None
    def __getitem__(self, name):
        return None
    def __setitem__(self, name, val):
        return None
    def back(self, n=1):
        return None
    def clear_history(self):
        return None
    def click(self, *args, **kwds):
        return None
    def click_link(self, link=None, **kwds):
        return None
    def close(self):
        return None
    def encoding(self):
        return None
    def find_link(self, text=None, text_regex=None, name=None, name_regex=None, url=None, url_regex=None, tag=None, predicate=None, nr=0):
        return None
    def follow_link(self, link=None, **kwds):
        return None
    def forms(self):
        return None
    def geturl(self):
        return None
    def global_form(self):
        return None
    def links(self, **kwds):
        return None
    def open_local_file(self, filename):
        return None
    def open(self, url, data=None, timeout=None):
        return None
    def open_novisit(self, url, data=None, timeout=None):
        return None
    def open_local_file(self, filename):
        return None
    def reload(self):
        return None
    def response(self):
        return None
    def select_form(self, name=None, predicate=None, nr=None, **attrs):
        return None
    def set_cookie(self, cookie_string):
        return None
    def set_handle_referer(self, handle):
        return None
    def set_header(self, header, value=None):
        return None
    def set_html(self, html, url="http://example.com/"):
        return None
    def set_response(self, response):
        return None
    def set_simple_cookie(self, name, value, domain, path='/'):
        return None
    def submit(self, *args, **kwds):
        return None
    def title(self):
        return None
    def viewing_html(self):
        return None
    def visit_response(self, response, request=None):
        return None
"""
    )


register_module_extender(MANAGER, "mechanize", mechanize_transform)
