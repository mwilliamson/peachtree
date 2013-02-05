import collections

from nose.tools import istest, assert_equal

from peachtree.human import dumps


@istest
def string_is_dumped_as_string_without_quotations():
    assert_equal("hello", dumps("hello"))


@istest
def integer_is_dumped_as_string():
    assert_equal("1", dumps(1))


@istest
def long_is_dumped_as_string():
    assert_equal("1", dumps(long(1)))


@istest
def long_is_dumped_as_string():
    assert_equal("1.2", dumps(1.2))


@istest
def booleans_are_dumped_as_lowercase_string():
    assert_equal("false", dumps(False))
    assert_equal("true", dumps(True))


@istest
def lists_are_dumped_with_each_element_on_new_line_preceded_by_hyphen():
    assert_equal("- 3\n- 2\n- 1", dumps([3, 2, 1]))
    
    
@istest
def nested_lists_cause_extra_indentation():
    assert_equal("- - 3\n  - 2\n", dumps([[3, 2]]))
    
    
@istest
def items_in_lists_are_separated_by_blank_line_if_they_are_multiline():
    assert_equal("- - 3\n  - 2\n\n- - 1\n  - 0\n", dumps([[3, 2], [1, 0]]))


@istest
def dumping_dicts_separates_key_and_value_with_colon_and_items_with_newlines():
    assert_equal(
        "one: 1\ntwo: 2",
        dumps(collections.OrderedDict([("one", 1), ("two", 2)]))
    )


@istest
def lists_within_dicts_are_on_newlines():
    assert_equal(
        "one:\n  - 3",
        dumps({"one": [3]})
    )


@istest
def values_within_dicts_are_indented_if_they_are_on_multiple_lines():
    assert_equal(
        "one:\n  - 3\n  - 2\n  - 1",
        dumps({"one": [3, 2, 1]})
    )
