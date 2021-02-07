from ctypes.util import find_library


def test_nglib_present():
    """Tests if ngspice shared library can be found with the ctypes find_library
    utility function.
    """

    lib = find_library("ngspice")
    assert lib is not None, "NgSpice shared library not found in system."
