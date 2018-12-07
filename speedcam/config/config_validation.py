
def remove_python_extension(file_name):
    # Check if there is a .py at the end of pluginName variable
    if file_name.endswith('.py'):
        return file_name[:-3]    # Remove .py extension
    else:
        return file_name


def enforce_lower_bound_float(value, bound):
    if value < bound:
        return bound
    else:
        return value
