from config.config_validation import *


def test_given_valid_python_filename_will_remove_extension():
    result = remove_python_extension('myfile.py')
    assert result == 'myfile'


def test_given_filename_is_not_python_no_changes():
    result = remove_python_extension('myfile.txt')
    assert result == 'myfile.txt'


def test_given_int_value_is_lower_than_bound_return_bound():
    result = enforce_lower_bound_int(1, 2)
    assert result == 2


def test_given_int_value_is_greater_than_bound_return_value():
    result = enforce_lower_bound_int(2, 1)
    assert result == 2


def test_given_float_value_is_lower_than_bound_return_bound():
    result = enforce_lower_bound_float(1.0, 2.0)
    assert result == 2.0


def test_given_float_value_is_greater_than_bound_return_value():
    result = enforce_lower_bound_float(2.1, 1.2)
    assert result == 2.1


def test_given_file_ext_remove_period():
    result = clean_file_ext_names('.py')
    assert result == 'py'


def test_given_file_ext_wthout_period_do_nothing():
    result = clean_file_ext_names('py')
    assert result == 'py'
