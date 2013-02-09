import argparse

from nose.tools import istest, assert_equal

from peachtree import arggroup


@istest
def empty_list_of_arguments_is_parsed_as_empty_list():
    argv = []
    
    parser = argparse.ArgumentParser()
    arggroup.add_repeatable_argument_group(parser, "--request")
    
    args = parser.parse_args(argv)
    assert_equal([], args.request)


@istest
def repeatable_argument_group_uses_subparser_to_parse_args():
    argv = ["--request", "--name", "server", "--image-name", "debian"]
    
    parser = argparse.ArgumentParser()
    group_parser = arggroup.add_repeatable_argument_group(parser, "--request")
    group_parser.add_argument("--name")
    group_parser.add_argument("--image-name")
    
    args = parser.parse_args(argv)
    assert_equal(1, len(args.request))
    assert_equal("server", args.request[0].name)
    assert_equal("debian", args.request[0].image_name)


@istest
def group_name_is_used_to_indicate_next_element():
    argv = [
        "--request", "--name", "server", "--image-name", "debian",
        "--request", "--name", "client", "--image-name", "ubuntu",
    ]
    
    parser = argparse.ArgumentParser()
    group_parser = arggroup.add_repeatable_argument_group(parser, "--request")
    group_parser.add_argument("--name")
    group_parser.add_argument("--image-name")
    
    args = parser.parse_args(argv)
    assert_equal(2, len(args.request))
    assert_equal("server", args.request[0].name)
    assert_equal("debian", args.request[0].image_name)
    assert_equal("client", args.request[1].name)
    assert_equal("ubuntu", args.request[1].image_name)
