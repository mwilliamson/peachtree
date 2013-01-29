from nose.tools import istest, assert_equal

from peachtree import dictobj


@istest
def conversion_from_dict_to_obj_uses_items_as_constructor_args():
    User = dictobj.data_class("User", ["username", "password"])
    
    input_dict = {"username": "bob", "password": "password1"}
    converted_user = dictobj.dict_to_obj(input_dict, User)
    
    expected_user = User("bob", "password1")
    assert_equal(expected_user, converted_user)


@istest
def arguments_with_camelcase_names_are_converted_to_use_underscores():
    User = dictobj.data_class("User", ["is_root"])
    
    input_dict = {"isRoot": True}
    converted_user = dictobj.dict_to_obj(input_dict, User)
    
    expected_user = User(is_root=True)
    assert_equal(expected_user, converted_user)


@istest
def conversion_from_obj_to_dict_uses_hacktastic_fields_property():
    User = dictobj.data_class("User", ["username", "password"])
    
    user = User("bob", "password1")
    result = dictobj.obj_to_dict(user)
    
    expected_dict = {"username": "bob", "password": "password1"}
    assert_equal(expected_dict, result)


@istest
def conversion_from_obj_to_dict_converts_underscores_to_camel_case():
    User = dictobj.data_class("User", ["is_root"])
    
    input_user = User(is_root=True)
    result = dictobj.obj_to_dict(input_user)
    
    expected_dict = {"isRoot": True}
    assert_equal(expected_dict, result)


@istest
def instances_of_data_class_are_equal_iff_all_fields_have_the_same_value():
    User = dictobj.data_class("User", ["username", "password"])
    
    assert User("bob", "password1") == User("bob", "password1")
    assert not User("jim", "password1") == User("bob", "password1")
    assert not User("bob", "password1") == User("bob", "password2")
    assert not User("jim", "password1") == User("bob", "password2")


@istest
def instances_of_data_class_are_not_equal_iff_any_fields_have_different_values():
    User = dictobj.data_class("User", ["username", "password"])
    
    assert not User("bob", "password1") != User("bob", "password1")
    assert User("jim", "password1") != User("bob", "password1")
    assert User("bob", "password1") != User("bob", "password2")
    assert User("jim", "password1") != User("bob", "password2")
