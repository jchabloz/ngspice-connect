#******************************************************************************
# This python script uses ctypes to implement C bindings for the shared library
# provided by ngspice. It allows to run a simulation and use all the power of
# Python to post-process and plots the results.
#
# References:
# [1] https://docs.python.org/3.8/library/ctypes.html#callback-functions
# [2] https://stackoverflow.com/questions/7259794/how-can-i-get-methods-to-work-as-callbacks-with-python-ctypes 
#******************************************************************************
from ctypes import Structure
from ctypes import c_double, c_char_p, c_int, c_short, c_int, c_bool, c_void_p
from ctypes import POINTER, CFUNCTYPE, CDLL, cast
from ctypes.util import find_library

from sys import stdout, stderr
import re
from tqdm import tqdm
from pandas import Series, DataFrame

#******************************************************************************
# Classes inheriting from ctypes Structure used to describe types passed to
# callback functions or received from exported functions.
#******************************************************************************
class NgComplex(Structure):
    _fields_ = [
        ("cx_real", c_double),
        ("cx_imag", c_double)
    ]

class VectorInfo(Structure):
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
        return self.v_length
    
    def __getitem__(self, key):
        """Allows vector data indexing and slicing."""
        if isinstance(key, int):
            if (key < 0) | (key >= len(self)):
                raise IndexError
        elif isinstance(key, slice):
            if not key.stop:
                key = slice(key.start, len(self), key.step)
            if key.start:
                if (key.start < 0):
                    raise IndexError("Index undershoot")
            if key.stop:
                if (key.stop > len(self)):
                    raise IndexError("Index overshoot")
        else:
            raise TypeError
        return self.v_realdata[key]
    
    def as_series(self):
        """Return a pandas Series object with vector data and name."""
        return Series(name=self.v_name.decode(), data=self[:])

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

#******************************************************************************
# Class NgSpice
#******************************************************************************
class NgSpice:

    _callbacks = []

    def write(self, msg):
        if self.pbar:
            self.pbar.write(msg)
        else:
            stdout.write(msg + '\n')

    #**************************************************************************
    # Callback functions
    # We define callback functions using the CFUNCTYPE factory as a decorator
    # (see [1]).
    # When needed, closure is used to wrap the ctypes callback functions in
    # order to promote access to "self" [2]. Note that in this case, the
    # factory needs to be assigned to an inner variable in order for it not to
    # get garbage collected. In our case, I use the self._callbacks[] array to
    # store them.
    #**************************************************************************
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
        """

        @CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
        def ng_send_stat_inner(value, libid, caller):

            match_percent = re.search(r"(\w+):\s+([0-9]*.?[0-9]*)%\s*$", value.decode()) 
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
                    self.pbar = tqdm(file=stdout, desc=name, total=100.0, unit='%')
                    self.pbar_value = 0.0
            else:
                self.write(value.decode())
            return 0
        
        return ng_send_stat_inner
    
    @CFUNCTYPE(c_int, c_int, c_bool, c_bool, c_int, c_void_p)
    def ng_controlled_exit(status, unload, exit, libid, caller):
        print("ng_controlled_exit: {} (unload={}, exit={})".format(status, unload, exit))
        return 0

    @CFUNCTYPE(c_int, POINTER(VecValuesAll), c_int, c_int, c_void_p)
    def ng_send_data(pvecvaluesall, count, libid, caller):
        #print("ng_send_data")
        return 0
    
    @CFUNCTYPE(c_int, POINTER(VecInfoAll), c_int, c_void_p)
    def ng_send_init_data(values, libid, caller):
        print("ng_send_init_data")
        return 0
    
    @CFUNCTYPE(c_int, c_bool, c_int, c_void_p)
    def ng_bg_thread_running(is_running, libid, caller):
        print("ng_bg_thread_running")
        return 0
    
    @CFUNCTYPE(c_int, c_int, c_double, c_double, c_char_p, c_void_p, c_int, c_int, c_int, c_void_p)
    def ng_send_evt_data(node_index, sim_time, value, print_value, data, size, mode, libid, caller):
        print("ng_send_evt_data")
        return 0
    
    @CFUNCTYPE(c_int, c_int, c_int, c_char_p, c_char_p, c_int, c_void_p)
    def ng_send_init_evt_data(node_index, max_index, name, udn_name, libid, caller):
        print("ng_send_init_evt_data")
        return 0

    def __init__(self):

        self.nglib = find_library('ngspice')
        if not self.nglib: 
            raise ValueError("Could not find ngspice library in the system")

        self.ng = CDLL(self.nglib)
        
        #Progress bar
        self.pbar = None
        self.pbar_value = 0.0

        #Initialize pointer to vec
        self.pvecvaluesall = None   
            
        #We need to assign the callbacks to inner variables in order to avoid them
        #to get garbage collected and the program to abort with SIGSEV!!!
        self._callbacks.append(self._ng_send_char())
        self._callbacks.append(self._ng_send_stat())
        
        #Initialize
        self.ng.ngSpice_Init(
            self._callbacks[0],
            self._callbacks[1],
            self.ng_controlled_exit,
            self.ng_send_data,
            self.ng_send_init_data,
            self.ng_bg_thread_running,
            None
        )

    def send_cmd(self, cmd):
        """Sends a spice command to the share ngspice library."""
        if not isinstance(cmd, bytes):
            if isinstance(cmd, str):
                cmd = cmd.encode('utf-8')
            else:
                raise TypeError
        self.ng.ngSpice_Command(cmd)

    def run(self):
        """Sends the run command to ngspice."""
        self.send_cmd("run")

    def quit(self):
        """Sends the quit command to ngspice."""
        self.send_cmd("quit")

    def get_cur_plot(self):
        """Returns the current plot."""
        return cast(self.ng.ngSpice_CurPlot(), c_char_p).value

    def get_all_plots(self):
        """Returns a list of all the available plots."""
        px = cast(self.ng.ngSpice_AllPlots(), POINTER(c_char_p))
        i = 0
        res = []
        while px[i]:
            res.append(px[i])
            i += 1
        return res

    def get_all_vecs(self, plot=None):
        """Returns a list of all available vectors for a given plot.
        Argument:
        plot = name of the plot, either as a bytes array or string.
        If plot is None (default), the current plot is used.
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

    def get_vec_info(self, vector):
        """Calls the ngGet_Vec_Info() ngspice exported function and returns a
        vector structure.
        Caveat: each time it is called, the object gets replaced. Results need
        to get stored somewhere else...
        """
        if not isinstance(vector, bytes):
            if isinstance(vector, str):
                vector = vector.encode('utf-8')
            else:
                raise TypeError
        vec_info = cast(self.ng.ngGet_Vec_Info(vector), POINTER(VectorInfo)).contents
        return vec_info

    def get_vector(self, vector):
        """Returns a simulated vector as a pandas Series object.
        Arguments:
        vector = vector name
        A list of all available vector names for a given plot can be obtained by using the
        get_all_vecs() function.
        Using a simple vector name will return values for the currently active plot.
        To access vectors from other plots, use <plot_name>.<vector_name> as argument.
        """
        vec_info = self.get_vec_info(vector)
        return vec_info.as_series()

    def get_all_vectors(self, plot=None):
        vec_names = self.get_all_vecs(plot)
        df = DataFrame()
        for v in vec_names:
            vec_info = self.get_vec_info(v)
            match_branch = re.search(r"(\w+)#branch$", v)
            if match_branch:
                v = "i(" + match_branch.group(1) + ")"
            df[v] = vec_info[:]
        return df

#EOF
