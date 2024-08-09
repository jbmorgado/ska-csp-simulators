import random


def generate_random_number(data_type, range_start, range_end):
    """
    Generate a random number of the specified data type within a given range.

    Args:
        data_type (str): The data type of the random number ('int' or 'float').
        range_start (int or float): The start of the range.
        range_end (int or float): The end of the range.

    Returns:
        int or float: A random number of the specified type within the given range.
    """
    if data_type == "int":
        return random.randint(range_start, range_end)
    elif data_type == "float":
        return random.uniform(range_start, range_end)
    else:
        raise ValueError("data_type must be 'int' or 'float'")
