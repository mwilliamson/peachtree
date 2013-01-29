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


@istest
def conversion_from_obj_to_dict_uses_hacktastic_fields_property():
    User = collections.namedtuple("User", ["username", "password"])
    
    user = User("bob", "password1")
    result = dictobj.obj_to_dict(user)
    
    expected_dict = {"username": "bob", "password": "password1"}
    assert_equal(expected_dict, result)


@istest
def conversion_from_obj_to_dict_converts_underscores_to_camel_case():
    User = collections.namedtuple("User", ["is_root"])
    
    input_user = User(is_root=True)
    result = dictobj.obj_to_dict(input_user)
    
    expected_dict = {"isRoot": True}
    assert_equal(expected_dict, result)
