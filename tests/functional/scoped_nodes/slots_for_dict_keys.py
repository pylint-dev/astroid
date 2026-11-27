class Issue(object):  # slots: id, id1
  SlotDefaults = {'id': 0, 'id1':1}
  __slots__ = SlotDefaults.keys()
