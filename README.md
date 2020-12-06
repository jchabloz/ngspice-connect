# ngspice-connect
A light Python package to connect with ngspice shared library.

## Context
I started this small project when I was evaluating the performances of the
[ngspice Spice simulator](http://ngspice.sourceforge.net/).
This simulator is a very fine piece of work, however it becomes a bit more
complex to learn how to use in order to produce plots, interactive or not,
or when it comes to managing complex testcases.

I thought that it would be great to directly control
ngspice from Python (e.g. from a Jupyter notebook), collect the simulation results, and directly use all the power offered by Python and its thousands of libraries.

Several packages can be found to interface with ngspice, such as [PySpice](https://pyspice.fabrice-salvaire.fr/).
However, what would be the fun in using already existing code?

As it turns out, Ngspice is nice enough to provide a (documented!) shared library interface, so this became an opportunity to learn how to use ctypes as well...