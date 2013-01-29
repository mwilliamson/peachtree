import re


def dict_to_obj(dict_kwargs, cls):
    cls_kwargs = dict(
        (_from_camel_case(key), value)
        for key, value in dict_kwargs.iteritems()
    )
    
    return cls(**cls_kwargs)


def obj_to_dict(obj):
    return dict(
        (_to_camel_case(key), getattr(obj, key))
        for key in obj._fields
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
