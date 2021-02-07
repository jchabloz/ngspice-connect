# ngspice-connect

A light Python package to connect with ngspice shared library.

## Context

I started this small project when I was evaluating the performances of the
[*Ngspice* Spice simulator](http://ngspice.sourceforge.net/). This simulator is
a very nice piece of work, however it is a bit limited if you want to produce
nice plots or when it comes to managing complex testcases.

I thought that it would be great to be able to directly control *Ngspice* from
Python (e.g. from a Jupyter notebook), collect the simulation results, and
directly use all the power offered by Python and its thousands of libraries to
post-process them.

Several projects can already be found to interface with *Ngspice*, such as
[PySpice](https://pyspice.fabrice-salvaire.fr/). However, what would be the fun
in using already existing code?

As it turns out, *Ngspice* is nice enough to provide a (well documented!) shared
library API, so this quickly turned out into an opportunity to learn how to use
ctypes as well...

## Howto

### Instantiating NgSpice

The functionality is essentially bundled into a single class: `NgSpice`.

```python
from ngspicex import NgSpice

ngx = NgSpice()
```

Optionally, a path to the shared library can be provided as an argument when
instantiating `NgSpice`. If none is provided, the provided ctypes library
finding mechanism will be used to try and locate it. An appropriate error is
raised upon failure.

### Sourcing a netlist and command file

The next logical step towards using the simulator is to define the circuit to
simulate. The simplest way to proceed would be to load a file with the required
circuit description (ie a netlist) and maybe some other stuff such as an
analysis description by using the `source()` method:

```python
ngx.source("path_to/netlist.cir")
```

Note that the `source()` method actually uses the `send_cmd()` method which can
be used to send any command recognized by *NgSpice* (see *NgSpice*'s own
documentation). The previous step could therefore alternatively be executed as

```python
ngx.send_cmd("source path_to/netlist.cir")
```

#### Alternative method

Another method that can be used instead of sourcing a spice command file is to
send it line by line by using the `send_circ()` method. For example, defining a
simple resistive divider with a DC voltage source and adding a command to
instruct the simulator to perform an operating point analysis could be performed
in the following way:

```python
ngx.send_circ(
    "*Resistive divider",
    "R1 n1 0 10k",
    "R2 n2 n1 10k",
    "V1 n2 0 DC 10",
    ".op",
    ".end"
)
```
**Warning**: At the moment, neither the `source()` nor the `send_circ()` methods
perform any kind of verification on the provided inputs. Any unvalid syntax will
most likely result in a segmentation fault.

*Ongoing work...*