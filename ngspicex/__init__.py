# *****************************************************************************
# This python script uses ctypes to implement C bindings for the shared library
# provided by ngspice. It allows to run a simulation and use all the power of
# Python to post-process and plots the results.
#
# References:
# [1] https://docs.python.org/3.8/library/ctypes.html#callback-functions
# [2] https://stackoverflow.com/questions/7259794/
# *****************************************************************************
from ctypes import Structure
from ctypes import c_double, c_char_p, c_short, c_int, c_bool, c_void_p
from ctypes import POINTER, CFUNCTYPE, CDLL, cast
from ctypes.util import find_library

from sys import stdout
from os import path
import re
from tqdm import tqdm
from pandas import Series, DataFrame
from numpy import array


__version__ = "1.1.0"


# *****************************************************************************
# Classes inheriting from ctypes Structure used to describe types passed to
# callback functions or received from exported functions.
# *****************************************************************************
class NgComplex(Structure):
    """Structure used to store a complex number."""
    _fields_ = [
        ("cx_real", c_double),
        ("cx_imag", c_double)
    ]


class VectorInfo(Structure):
    """Structure used to store a simulated vector data and info"""
    _fields_ = [
        ("v_name", c_char_p),
        ("v_type", c_int),
        ("v_flags", c_short),
        ("v_realdata", POINTER(c_double)),
        ("v_compdata", POINTER(NgComplex)),
        ("v_length", c_int)
    ]

    def __repr__(self):
        return "VectorInfo structure: " + self.v_name.decode()

    def __len__(self):
        """Allows to query the length of a vector with the len() method"""
        return self.v_length

    def __getitem__(self, key):
        """Allows vector data indexing and slicing."""
        # TODO: Check type and return real or complex data.
        if isinstance(key, int):
            if (key < 0) | (key >= len(self)):
                raise IndexError
        elif isinstance(key, slice):
            if not key.stop:
                key = slice(key.start, len(self), key.step)
            if key.start:
                if (key.start < 0):
                    raise IndexError("Index cannot be negative")
            if key.stop:
                if (key.stop > len(self)):
                    raise IndexError("Index too large")
        else:
            raise TypeError

        # Check if v_realdata is a NULL pointer using bool()
        # Return None if NULL pointer.
        if (bool(self.v_realdata)):
            return self.v_realdata[key]
        else:
            return None

    def as_series(self):
        """Return a pandas Series object with vector data and name."""
        return Series(name=self.v_name.decode(), data=self[:])

    def as_array(self):
        """Return a numpy array object with vector data."""
        return array(self[:])


class VecInfo(Structure):
    _fields_ = [
        ("number", c_int),
        ("vecname", c_char_p),
        ("is_real", c_bool),
        ("pdvec", c_void_p),
        ("pdvecscale", c_void_p)
    ]


class VecInfoAll(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("title", c_char_p),
        ("date", c_char_p),
        ("type", c_char_p),
        ("veccount", c_int),
        ("vecs", POINTER(VecInfo))
    ]


class VecValues(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("creal", c_double),
        ("cimag", c_double),
        ("is_scale", c_bool),
        ("is_complex", c_bool)
    ]


class VecValuesAll(Structure):
    _fields_ = [
        ("veccount", c_int),
        ("vecindex", c_int),
        ("vecsa", POINTER(VecValues))
    ]


# *****************************************************************************
# Class NgSpice - Main class
# *****************************************************************************
class NgSpice:

    def write(self, msg):
        """Writes to stdout or progress bar.
        Argument: msg -- Message to be written.
        """
        self._msg = msg
        if not self._silent:
            if self.pbar:
                self.pbar.write(msg)
            else:
                stdout.write(msg + '\n')

    # *************************************************************************
    # Callback functions
    # We define callback functions using the CFUNCTYPE factory as a decorator
    # (see [1]).
    # When needed, closure is used to wrap the ctypes callback functions in
    # order to promote access to "self" [2]. Note that in this case, the
    # factory needs to be assigned to an inner variable in order for it not to
    # get garbage collected. In our case, I use the self._callbacks[] array to
    # store them.
    # *************************************************************************

    def _ng_send_char(self):
        """Factory function -- returns a callback function to receive stdout/stderr
        output from libngspice.
        """

        @CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
        def ng_send_char_inner(value, libid, caller):

            if value.startswith(b"stdout"):
                self.write(value.decode()[len("stdout"):])
            elif value.startswith(b"stderr"):
                self.write(value.decode()[len("stderr"):])
            else:
                self.write(value.decode())
            return 0

        return ng_send_char_inner

    def _ng_send_stat(self):
        """Factory function -- returns a callback function used to receive relevant
        statistics for the currently running simulation.
        This functions updates a progress bar (implemented with tqdm) if the
        class is instantiated with the keyword use_progress_bar=True (False by
        default).
        """

        @CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
        def ng_send_stat_inner(value, libid, caller):

            match_percent = re.search(
                r"(\w+):\s+([0-9]*.?[0-9]*)%\s*$", value.decode())
            if not self._silent:
                if match_percent:
                    name = match_percent.group(1)
                    percentage = float(match_percent.group(2))

                    if self.pbar:
                        self.pbar.update(percentage - self.pbar_value)
                        self.pbar_value = percentage
                        if percentage >= 99.9:
                            self.pbar.update(100.0 - self.pbar_value)
                            self.pbar.close()
                            self.pbar = None
                    else:
                        if self.use_progress_bar:
                            self.pbar = tqdm(
                                file=stdout, desc=name, total=100.0, unit='%')
                            self.pbar_value = 0.0
                else:
                    self.write(value.decode())
            return 0

        return ng_send_stat_inner

    def _ng_controlled_exit(self):
        """Factory function -- returns a callback function called from shared library
        on exit, e.g. when using the quit command.
        """

        @CFUNCTYPE(c_int, c_int, c_bool, c_bool, c_int, c_void_p)
        def ng_controlled_exit_inner(status, unload, exit, libid, caller):
            print("ng_controlled_exit: {} (unload={}, exit={})".format(
                status, unload, exit))
            return 0

        return ng_controlled_exit_inner

    def _ng_send_data(self):
        """Factory function -- returns a callback function called from shared library
        at each simulated data point.
        """

        @CFUNCTYPE(c_int, POINTER(VecValuesAll), c_int, c_int, c_void_p)
        def ng_send_data_inner(pvecvaluesall, count, libid, caller):
            return 0

        return ng_send_data_inner

    def _ng_send_init_data(self):
        """Factory function -- returns a callback function called from shared library
        at simulation initialization.
        """

        @CFUNCTYPE(c_int, POINTER(VecInfoAll), c_int, c_void_p)
        def ng_send_init_data_inner(values, libid, caller):
            self.write("ng_send_init_data")
            return 0

        return ng_send_init_data_inner

    def _ng_bg_thread_running(self):
        """Factory function -- returns a callback function called from shared library.
        TODO: document functionality
        """

        @CFUNCTYPE(c_int, c_bool, c_int, c_void_p)
        def ng_bg_thread_running_inner(is_running, libid, caller):
            self.write("ng_bg_thread_running")
            return 0

        return ng_bg_thread_running_inner

    def _ng_send_evt_data(self):
        """Factory function -- returns a callback function called from shared library.
        TODO: document functionality
        """

        @CFUNCTYPE(c_int, c_int, c_double, c_double, c_char_p, c_void_p, c_int,
                   c_int, c_int, c_void_p)
        def ng_send_evt_data_inner(node_index, sim_time, value, print_value,
                                   data, size, mode, libid, caller):
            self.write("ng_send_evt_data")
            return 0

        return ng_send_evt_data_inner

    def _ng_send_init_evt_data(self):
        """Factory function -- returns a callback function called from shared library.
        TODO: document functionality
        """

        @CFUNCTYPE(c_int, c_int, c_int, c_char_p, c_char_p, c_int, c_void_p)
        def ng_send_init_evt_data_inner(node_index, max_index, name, udn_name,
                                        libid, caller):
            self.write("ng_send_init_evt_data")
            return 0

        return ng_send_init_evt_data_inner

    def __init__(self, **kwargs):
        """NgSpice Class
        Possible keywords arguments:
        * libpath: defines an alternative path for the shared library. If not
          defined, the library is automatically searched with the appropriate
          ctypes mechanism.
        * use_progress_bar: boolean (default: False). If True, a tqdm progress
          bar is used to represent the progress statistics sent by the shared
          library to the "send_stat" callback function.
          **Warning** The statistics sent to the callback function seems not to
          be working for Ngspice version > 31. If you try and use progress bars
          for later versions, it will not function properly.
        """

        # Alternative path to shared library
        if "libpath" in kwargs:
            self.nglib = kwargs["libpath"]
        else:
            self.nglib = find_library('ngspice')
            if not self.nglib:
                raise ValueError(
                    "Could not find ngspice library in the system")

        # Enables usage of tqdm progress bars based on sent statistics
        if "use_progress_bar" in kwargs:
            if not isinstance(kwargs["use_progress_bar"], bool):
                raise TypeError
            self.use_progress_bar = kwargs["use_progress_bar"]
        else:
            self.use_progress_bar = False

        # DLL attached
        self.ng = CDLL(self.nglib)
        self._attached = True

        # Outputs management
        self._silent = False
        self._msg = ""

        # Progress bar
        self.pbar = None
        self.pbar_value = 0.0

        # Initialize pointer to vec
        self.pvecvaluesall = None

        # We need to assign the callbacks to inner variables in order to avoid
        # them to get garbage collected and the program to abort with SIGSEV!!!
        self._callbacks = {}
        self._callbacks["send_char"] = self._ng_send_char()
        self._callbacks["send_stat"] = self._ng_send_stat()
        self._callbacks["exit"] = self._ng_controlled_exit()
        self._callbacks["send_data"] = self._ng_send_data()
        self._callbacks["send_init_data"] = self._ng_send_init_data()
        self._callbacks["bg_thread_running"] = self._ng_bg_thread_running()

        # Initialize
        self.ng.ngSpice_Init(
            self._callbacks["send_char"],
            self._callbacks["send_stat"],
            self._callbacks["exit"],
            self._callbacks["send_data"],
            self._callbacks["send_init_data"],
            self._callbacks["bg_thread_running"],
            None
        )

    def send_cmd(self, cmd, silent=False):
        """Sends a spice command to the shared ngspice library.
        Arguments:
        cmd: Command
        silent: If True (default=False), no message is sent to stdout/stderr.
        """
        if not isinstance(cmd, bytes):
            if isinstance(cmd, str):
                cmd = cmd.encode('utf-8')
            else:
                raise TypeError
        self._silent = silent
        self.ng.ngSpice_Command(cmd)
        self._silent = False

    def send_circ(self, *args, **kwargs):
        """Sends a circuit description to the shared ngspice library.
        A circuit description consists out of an array of commands as they
        would be found in a spice command file (see ngspice documentation). The
        last command has to be ".end" to finalize the circuit loading.
        !!!Warning: any error in the sent circuit description will likely
        result in a segmentation fault. There is no parsing of the arguments to
        assess their validity prior to sending it to the shared library.
        """

        # We create a class corresponding to an array of null-terminated
        # strings. C equivalent would be char**. We add 1 extra element to make
        # sure that the array final element is a NULL string, as required.
        CircType = c_char_p * (len(args) + 1)
        circ_array = CircType()

        for i, v in enumerate(args):
            if not isinstance(v, str):
                raise ValueError
            circ_array[i] = v.encode('utf-8')

        if 'silent' in kwargs:
            self._silent = kwargs['silent']
        ret = self.ng.ngSpice_Circ(circ_array)
        if ret != 0:
            raise RuntimeError("Error while loading circuit")
        self._silent = False

    def source(self, filepath):
        """Loads (sources) a spice command file."""
        if not path.isfile(filepath):
            raise FileNotFoundError
        self.send_cmd("source " + filepath)

    def run(self, rawfile="", silent=False):
        """Sends the run command to ngspice (shortcut).
        Arguments:
        silent: If True (default=False), no message is sent to stdout/stderr.
        """
        if rawfile != "":
            self.send_cmd("run " + rawfile, silent)
        else:
            self.send_cmd("run", silent)

    def reset(self, silent=True):
        """Sends the reset command to ngspice (shortcut).
        Arguments:
        silent: If True (default=True), no message is sent to stdout/stderr.
        """
        self.send_cmd("reset", silent)

    def quit(self):
        """Sends the quit command to ngspice."""
        if self._attached:
            self.send_cmd("quit")
            self._attached = False
        else:
            print("DLL already detached...")

    def get_cur_plot(self):
        """Returns the name of the current plot."""
        curplot = self.ng.ngSpice_CurPlot
        curplot.restype = c_char_p
        return curplot().decode()

    def get_all_plots(self):
        """Returns a list of all the available plots."""
        px = cast(self.ng.ngSpice_AllPlots(), POINTER(c_char_p))
        i = 0
        res = []
        while px[i]:
            res.append(px[i].decode())
            i += 1
        return res

    def get_all_vecs(self, plot=None):
        """Returns a list of all available vectors for a given plot.
        Argument:
        plot: name of the plot, either as a bytes array or string. If plot is
        not defined or None, the current plot is used.
        """
        if not plot:
            plot = self.get_cur_plot()
        if not isinstance(plot, bytes):
            if isinstance(plot, str):
                plot = plot.encode('utf-8')
            else:
                raise TypeError

        pvecs = cast(self.ng.ngSpice_AllVecs(plot), POINTER(c_char_p))
        res = []
        i = 0
        while pvecs[i]:
            res.append(plot.decode() + "." + pvecs[i].decode())
            i += 1
        return res

    def _get_vec_info(self, vector):
        """Calls the ngGet_Vec_Info() ngspice exported function and returns a
        VectorInfo structure object.
        Intended to stay as a private method. Use get_vector or get_all_vectors
        to access vector data.
        Caveat: each time this method is used, the object actually gets
        replaced.
        """
        if not isinstance(vector, bytes):
            if isinstance(vector, str):
                vector = vector.encode('utf-8')
            else:
                raise TypeError
        vec_info = cast(self.ng.ngGet_Vec_Info(vector),
                        POINTER(VectorInfo)).contents
        return vec_info

    def get_vector(self, vector):
        """Returns a simulated vector as a pandas Series object.
        Arguments:
        vector: vector name
        A list of all available vector names for a given plot can be obtained
        by using the get_all_vecs() function. Using a simple vector name will
        return values for this vector in the currently active plot. To access
        vectors from other plots than the current one, use
        <plot_name>.<vector_name> as argument.
        """
        vec_info = self._get_vec_info(vector)
        return vec_info.as_series()

    def get_all_vectors(self, plot=None):
        """Returns all the available vectors for a given plot in a pandas
        DataFrame object.
        Arguments:
        plot: name of the plot from which to collect available vectors. If plot
        is not defined or None, the current plot is used.
        """
        vec_names = self.get_all_vecs(plot)
        df = DataFrame()
        for v in vec_names:
            vec_info = self._get_vec_info(v)
            vec_name = vec_info.v_name.decode()
            match_branch = re.search(r"(\w+)#branch$", vec_name)
            if match_branch:
                vec_name = "i(" + match_branch.group(1) + ")"
            df[vec_name] = vec_info[:]
        return df

    @property
    def temp(self):
        self.send_cmd("echo $temp", True)
        self._temp = float(self._msg)
        return self._temp

    @temp.setter
    def temp(self, value):
        self.send_cmd("set temp={}".format(value))
        self._temp = value


# EOF
