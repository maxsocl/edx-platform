# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.1+capsulehack
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.
# This file is compatible with both classic and new-style classes.

from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_coo', [dirname(__file__)])
        except ImportError:
            import _coo
            return _coo
        if fp is not None:
            try:
                _mod = imp.load_module('_coo', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _coo = swig_import_helper()
    del swig_import_helper
else:
    import _coo
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static) or hasattr(self,name):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0



def coo_count_diagonals(*args):
    """coo_count_diagonals(int nnz, int Ai, int Aj) -> int"""
    return _coo.coo_count_diagonals(*args)


def coo_tocsr(*args):
    """
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, signed char Ax,
        int Bp, int Bj, signed char Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned char Ax,
        int Bp, int Bj, unsigned char Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, short Ax,
        int Bp, int Bj, short Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned short Ax,
        int Bp, int Bj, unsigned short Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, int Ax,
        int Bp, int Bj, int Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned int Ax,
        int Bp, int Bj, unsigned int Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, long long Ax,
        int Bp, int Bj, long long Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned long long Ax,
        int Bp, int Bj, unsigned long long Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, float Ax,
        int Bp, int Bj, float Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, double Ax,
        int Bp, int Bj, double Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, long double Ax,
        int Bp, int Bj, long double Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, npy_cfloat_wrapper Ax,
        int Bp, int Bj, npy_cfloat_wrapper Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, npy_cdouble_wrapper Ax,
        int Bp, int Bj, npy_cdouble_wrapper Bx)
    coo_tocsr(int n_row, int n_col, int nnz, int Ai, int Aj, npy_clongdouble_wrapper Ax,
        int Bp, int Bj, npy_clongdouble_wrapper Bx)
    """
    return _coo.coo_tocsr(*args)

def coo_tocsc(*args):
    """
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, signed char Ax,
        int Bp, int Bi, signed char Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned char Ax,
        int Bp, int Bi, unsigned char Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, short Ax,
        int Bp, int Bi, short Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned short Ax,
        int Bp, int Bi, unsigned short Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, int Ax,
        int Bp, int Bi, int Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned int Ax,
        int Bp, int Bi, unsigned int Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, long long Ax,
        int Bp, int Bi, long long Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned long long Ax,
        int Bp, int Bi, unsigned long long Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, float Ax,
        int Bp, int Bi, float Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, double Ax,
        int Bp, int Bi, double Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, long double Ax,
        int Bp, int Bi, long double Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, npy_cfloat_wrapper Ax,
        int Bp, int Bi, npy_cfloat_wrapper Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, npy_cdouble_wrapper Ax,
        int Bp, int Bi, npy_cdouble_wrapper Bx)
    coo_tocsc(int n_row, int n_col, int nnz, int Ai, int Aj, npy_clongdouble_wrapper Ax,
        int Bp, int Bi, npy_clongdouble_wrapper Bx)
    """
    return _coo.coo_tocsc(*args)

def coo_todense(*args):
    """
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, signed char Ax,
        signed char Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned char Ax,
        unsigned char Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, short Ax,
        short Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned short Ax,
        unsigned short Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, int Ax,
        int Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned int Ax,
        unsigned int Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, long long Ax,
        long long Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, unsigned long long Ax,
        unsigned long long Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, float Ax,
        float Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, double Ax,
        double Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, long double Ax,
        long double Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, npy_cfloat_wrapper Ax,
        npy_cfloat_wrapper Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, npy_cdouble_wrapper Ax,
        npy_cdouble_wrapper Bx)
    coo_todense(int n_row, int n_col, int nnz, int Ai, int Aj, npy_clongdouble_wrapper Ax,
        npy_clongdouble_wrapper Bx)
    """
    return _coo.coo_todense(*args)

def coo_matvec(*args):
    """
    coo_matvec(int nnz, int Ai, int Aj, signed char Ax, signed char Xx,
        signed char Yx)
    coo_matvec(int nnz, int Ai, int Aj, unsigned char Ax, unsigned char Xx,
        unsigned char Yx)
    coo_matvec(int nnz, int Ai, int Aj, short Ax, short Xx, short Yx)
    coo_matvec(int nnz, int Ai, int Aj, unsigned short Ax, unsigned short Xx,
        unsigned short Yx)
    coo_matvec(int nnz, int Ai, int Aj, int Ax, int Xx, int Yx)
    coo_matvec(int nnz, int Ai, int Aj, unsigned int Ax, unsigned int Xx,
        unsigned int Yx)
    coo_matvec(int nnz, int Ai, int Aj, long long Ax, long long Xx,
        long long Yx)
    coo_matvec(int nnz, int Ai, int Aj, unsigned long long Ax, unsigned long long Xx,
        unsigned long long Yx)
    coo_matvec(int nnz, int Ai, int Aj, float Ax, float Xx, float Yx)
    coo_matvec(int nnz, int Ai, int Aj, double Ax, double Xx, double Yx)
    coo_matvec(int nnz, int Ai, int Aj, long double Ax, long double Xx,
        long double Yx)
    coo_matvec(int nnz, int Ai, int Aj, npy_cfloat_wrapper Ax, npy_cfloat_wrapper Xx,
        npy_cfloat_wrapper Yx)
    coo_matvec(int nnz, int Ai, int Aj, npy_cdouble_wrapper Ax, npy_cdouble_wrapper Xx,
        npy_cdouble_wrapper Yx)
    coo_matvec(int nnz, int Ai, int Aj, npy_clongdouble_wrapper Ax,
        npy_clongdouble_wrapper Xx, npy_clongdouble_wrapper Yx)
    """
    return _coo.coo_matvec(*args)
