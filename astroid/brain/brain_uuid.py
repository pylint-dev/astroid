# Copyright (c) 2017-2018, 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE

"""Astroid hooks for the UUID module."""


from astroid import MANAGER, nodes


def _patch_uuid_class(node):
    # The .int member is patched using __dict__
    node.locals["int"] = [nodes.Const(0, parent=node)]


MANAGER.register_transform(
    nodes.ClassDef, _patch_uuid_class, lambda node: node.qname() == "uuid.UUID"
)
