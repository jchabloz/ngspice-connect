# ngspice-connect
A light Python package to connect with ngspice shared library.

## Context

I started this small project when I was evaluating the performances of the
[*Ngspice* Spice simulator](http://ngspice.sourceforge.net/).
This simulator is a f`kkkkine piece of work, however it is a bit limited if you
want to produce nice plots or when it comes to managing complex testcases.

I thought that it would be great to be able to directly control *Ngspice*
from Python (e.g. from a Jupyter notebook), collect the simulation results,
and directly use all the power offered by Python and its thousands of libraries
to post-process them.

Several projects can already be found to interface with *Ngspice*, such as
[PySpice](https://pyspice.fabrice-salvaire.fr/).
However, what would be the fun in using already existing code?

As it turns out, *Ngspice* is nice enough to provide a (well documented!)
shared library API, so this quickly turned out into an opportunity to learn
how to use ctypes as well...

## Howto

### Instantiating NgSpice

The functionality is essentially bundled into a single class: `NgSpice`.

```python
from ngspicex import NgSpice

ngx = NgSpice()
```

Optionally, a path to the shared library can be provided as an argument
when instantiating `NgSpice`. If none is provided, the provided ctypes
library finding mechanism will be used to try and locate it.
An appropriate error is raised upon failure.

### Sourcing a netlist and command file

THe next logical step towards using the simulator is to define the
circuit to simulate.
The simplest way to proceed would be to load a file with the required
circuit description (ie a netlist) and maybe some other stuff such as
an analysis description by using the `source()` method:

```python
ngx.source("path_to/netlist.cir")
```

*Ongoing work...*