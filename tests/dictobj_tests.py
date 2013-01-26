import collections

from nose.tools import istest, assert_equal

from peachtree import dictobj


@istest
def conversion_from_dict_to_obj_uses_items_as_constructor_args():
    User = collections.namedtuple("User", ["username", "password"])
    
    input_dict = {"username": "bob", "password": "password1"}
    converted_user = dictobj.dict_to_obj(input_dict, User)
    
    expected_user = User("bob", "password1")
    assert_equal(expected_user, converted_user)


@istest
def arguments_with_camelcase_names_are_converted_to_use_underscores():
    User = collections.namedtuple("User", ["is_root"])
    
    input_dict = {"isRoot": True}
    converted_user = dictobj.dict_to_obj(input_dict, User)
    
    expected_user = User(is_root=True)
    assert_equal(expected_user, converted_user)
