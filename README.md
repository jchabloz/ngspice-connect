# ngspice-connect
A light Python package to connect with ngspice shared library.

## Context
I started this small project when I was evaluating the performances of the
ngspice Spice simulator.
This simulator is a very fine piece of work, however it becomes a bit more
complex to learn how to use in order to produce plots, interactive or not,
or when it comes to managing complex testcases.

I thought that it would be great if it would be possible to directly control
ngspice from Python, collect the simulation results, and directly use all the
power offered by Python and its thousands of libraries.

Several packages can be found to interface with ngspice, such as PySpice.
However, what would be the fun in using an already existing piece of code?

Ngspice is nice enough to provide a (documented!) shared library interface, 
so this became an opportunity to learn how to use ctypes as well...