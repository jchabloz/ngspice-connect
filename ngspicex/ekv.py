# *****************************************************************************
# Miscellaneous methods linked to the EKV MOS model "hand" calculation.
# *****************************************************************************
from math import sqrt, log, exp


_kB = 1.3806488e-23     # Boltzmann constant
_T0 = 273.15            # 0 degrees Celsius in Kelvin
_qe = 1.60217657e-19    # Elementary charge


def gekv(i):
    """Normalized EKV transconductance function."""
    return sqrt(0.25 + i) - 0.5


def fekv_inv(i):
    """Normalized inverse EKV function."""
    return 2.0*gekv(i) + log(gekv(i))


def fekv(u, prec=1e-9):
    """Normalized EKV function.
    Solved using a Newton-Raphson steepest descent recursive algorithm."""
    ix = 1.0e-16

    if (u < -15):
        return exp(u)
    else:
        vx = fekv_inv(ix)
        while (abs(u - vx) > prec):
            vx = fekv_inv(ix)
            ix += (u - vx)*gekv(ix)
        return ix


def ut(temp):
    """Thermodynamic voltage"""
    return _kB*(temp + _T0)/_qe


# EOF
