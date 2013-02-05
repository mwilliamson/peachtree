def dumps(value):
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif isinstance(value, (int, long, float, basestring)):
        return str(value)
    elif isinstance(value, list):
        return "\n".join(
            _dumps_element(element)
            for element in value
        )
    elif isinstance(value, dict):
        return "\n".join(
            "{0}:{1}".format(dumps(item_key), _dumps_item_value(item_value))
            for item_key, item_value in value.iteritems()
        )


def _dumps_element(element):
    output = _indent(dumps(element))
    if _is_scalar(element):
        return "- {0}".format(output)
    else:
        return "- {0}\n".format(output)


def _dumps_item_value(item_value):
    output = _indent(dumps(item_value))
    if _is_scalar(item_value):
        return " {0}".format(output)
    else:
        return "\n  {0}".format(output)


def _is_scalar(value):
    return not isinstance(value, (list, dict))


def _indent(value):
    return value.replace("\n", "\n  ")

