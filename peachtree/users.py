from . import dictobj


User = dictobj.data_class("User", ["username", "password", "is_root"])
