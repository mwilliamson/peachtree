import re


def dict_to_obj(dict_kwargs, cls):
    cls_kwargs = dict(
        (_from_camel_case(key), value)
        for key, value in dict_kwargs.iteritems()
    )
    
    return cls(**cls_kwargs)


def _from_camel_case(string):
    # http://stackoverflow.com/questions/1175208
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
