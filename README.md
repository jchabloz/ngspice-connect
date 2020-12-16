# ngspice-connect
A light Python package to connect with ngspice shared library.

## Context

I started this small project when I was evaluating the performances of the
[*Ngspice* Spice simulator](http://ngspice.sourceforge.net/).
This simulator is a fine piece of work, however it is a bit limited if you
want to produce nice plots or when it comes to managing complex testcases.

I thought that it would be great to be able to directly control *Ngspice*
from Python (e.g. from a Jupyter notebook), collect the simulation results, and directly use all the power offered by Python and its thousands of libraries to post-process them.

Several projects can already be found to interface with *Ngspice*, such as [PySpice](https://pyspice.fabrice-salvaire.fr/).
However, what would be the fun in using already existing code?

As it turns out, *Ngspice* is nice enough to provide a (well documented!) shared library API, so this quickly turned out into an opportunity to learn how to use ctypes as well...