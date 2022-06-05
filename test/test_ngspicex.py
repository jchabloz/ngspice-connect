from ngspicex import NgSpice
import pytest


@pytest.fixture
def ngx():
    return NgSpice()


def test_ngspice_class_instance(ngx):
    """Tests NgSpice instantiation"""
    assert isinstance(ngx, NgSpice)


def test_ngspice_write(ngx, capsys):
    """Tests NgSpice write method"""
    str_test = "This is a test string"
    ngx.write(str_test)
    assert capsys.readouterr().out == str_test + '\n'


def test_ngspice_send_cmd(ngx, capsys):
    """Tests NgSpice send_cmd method"""
    str_test = "This is a test message"
    ngx.send_cmd(f"echo {str_test}")

    assert capsys.readouterr().out == ' ' + str_test + '\n'
    ngx.send_cmd("non_existing_cmd")

    assert (capsys.readouterr().out ==
            ' non_existing_cmd: no such command available in ngspice\n')

    with pytest.raises(TypeError):
        ngx.send_cmd(1)
