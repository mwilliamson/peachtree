import re
import uuid
import collections


def dict_to_obj(dict_kwargs, cls):
    dict_kwargs_without_camel_case = dict(
        (_from_camel_case(key), value)
        for key, value in dict_kwargs.iteritems()
    )
    
    cls_kwargs = dict(
        (key, value)
        for key, value in dict_kwargs_without_camel_case.iteritems()
        if key in getattr(cls, _fields_attr)
    )
    
    return cls(**cls_kwargs)


def obj_to_dict(obj):
    return collections.OrderedDict(
        (_to_camel_case(key), getattr(obj, key))
        for key in getattr(obj, _fields_attr)
    )


def _from_camel_case(string):
    # http://stackoverflow.com/questions/1175208
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _to_camel_case(value):
    # http://stackoverflow.com/questions/4303492
    def camelcase(): 
        yield lambda s: s.lower()
        while True:
            yield lambda s: s.capitalize()

    c = camelcase()
    return "".join(c.next()(x) if x else '_' for x in value.split("_"))


_fields_attr = str(uuid.uuid4())


def data_class(name, fields):
    def __init__(self, *args, **kwargs):
        for field_index, field_name in enumerate(fields):
            if field_index < len(args):
                setattr(self, field_name, args[field_index])
            elif field_name in kwargs:
                setattr(self, field_name, kwargs.pop(field_name))
            else:
                raise TypeError("Missing argument: {0}".format(field_name))
                
        for field_name in kwargs.iterkeys():
            raise TypeError("{0}.__init__ does not take keyword argument {1}".format(name, field_name))
    
    def __eq__(self, other):
        if isinstance(other, new_type):
            return all(
                getattr(self, field_name) == getattr(other, field_name)
                for field_name in fields
            )
        else:
            return NotImplemented
        
    def __ne__(self, other):
        return not (self == other)
        
    def __repr__(self):
        values = (getattr(self, field_name) for field_name in fields)
        return "{0}({1})".format(name, ", ".join(values))
        
    def __str__(self):
        return repr(self)
    
    properties = {
        "__init__": __init__,
        "__eq__": __eq__,
        "__ne__": __ne__,
        "__repr__": __repr__,
        "__str__": __str__,
        _fields_attr: fields,
    }
    
    new_type = type(name, (object,), properties)
    return new_type
