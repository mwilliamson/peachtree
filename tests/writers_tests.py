import StringIO

from nose.tools import istest, assert_equal

from peachtree import writers


@istest
def json_writer_converts_values_to_json():
    output = StringIO.StringIO()
    
    writer = writers.find_writer_by_name("json", output)
    writer.write_result(["one", 2, False])
    expected_output = (
        '[\n'
        '    "one",\n'
        '    2,\n'
        '    false\n'
        ']\n'
    )
    assert_equal(expected_output, output.getvalue())
    
