def dumps(value):
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif isinstance(value, (int, long, float, basestring)):
        return str(value)
    elif isinstance(value, list):
        return "\n".join(
            "- {0}".format(_indent(dumps(element)))
            for element in value
        )
    elif isinstance(value, dict):
        return "\n".join(
            "{0}:{1}".format(dumps(item_key), _dumps_item_value(item_value))
            for item_key, item_value in value.iteritems()
        )


def _dumps_item_value(item_value):
    output = _indent(dumps(item_value))
    if isinstance(item_value, (list, dict)):
        return "\n  {0}".format(output)
    else:
        return " {0}".format(output)


def _indent(value):
    return value.replace("\n", "\n  ")
