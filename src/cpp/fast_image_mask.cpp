#include <Python.h>
#include <iostream>
#include <Magick++.h>
#include "FSET_ports.h"
#include <string>

using namespace std;
using namespace Magick;

// Comments and tutorial courtesy of http://adamlamers.com/post/NUBSPFQJ50J1
// Actual module method definition - this is the code that will be called by
// hello_module.print_hello_world
static PyObject * create_night(PyObject *self, PyObject *args) {
    InitializeMagick("");
    char *imgName, *outName, *maskName;
    if (!PyArg_ParseTuple(args, "zzz", &imgName, &outName, &maskName)) {
        return NULL;
    }

    c_create_night(imgName, outName, maskName);

    Py_RETURN_NONE;
}

static PyObject * create_hard_winter(PyObject *self, PyObject *args) {
    InitializeMagick("");
    char *imgName, *outName, *maskName;
    if (!PyArg_ParseTuple(args, "zzz", &imgName, &outName, &maskName)) {
        return NULL;
    }

    c_create_hard_winter(imgName, outName, maskName);

    Py_RETURN_NONE;
}

static PyObject * create_autumn(PyObject *self, PyObject *args) {
    InitializeMagick("");
    char *imgName, *outName, *maskName;
    if (!PyArg_ParseTuple(args, "zzz", &imgName, &outName, &maskName)) {
        return NULL;
    }

    c_create_autumn(imgName, outName, maskName);

    Py_RETURN_NONE;
}

static PyObject * create_spring(PyObject *self, PyObject *args) {
    InitializeMagick("");
    char *imgName, *outName, *maskName;
    if (!PyArg_ParseTuple(args, "zzz", &imgName, &outName, &maskName)) {
        return NULL;
    }

    c_create_spring(imgName, outName, maskName);

    Py_RETURN_NONE;
}

static PyObject * create_winter(PyObject *self, PyObject *args) {
    InitializeMagick("");
    char *imgName, *outName, *maskName;
    if (!PyArg_ParseTuple(args, "zzz", &imgName, &outName, &maskName)) {
        return NULL;
    }

    c_create_winter(imgName, outName, maskName);

    Py_RETURN_NONE;
}
// Method definition object for this extension, these argumens mean:
// ml_name: The name of the method
// ml_meth: Function pointer to the method implementation
// ml_flags: Flags indicating special features of this method, such as
//           accepting arguments, accepting keyword arguments, being a
//           class method, or being a static method of a class.
// ml_doc:  Contents of this method's docstring
static PyMethodDef fast_image_mask_functions[] = { 
    {
        "create_night",
        create_night,
        //METH_NOARGS,
        METH_VARARGS,
        "Create night mask image named outName from imgName image"
    },
    {
        "create_hard_winter",
        create_hard_winter,
        //METH_NOARGS,
        METH_VARARGS,
        "Create hard winter image named outName from imgName image"
    },
    {
        "create_autumn",
        create_autumn,
        //METH_NOARGS,
        METH_VARARGS,
        "Create autumn image named outName from imgName image"
    },
    {
        "create_spring",
        create_spring,
        //METH_NOARGS,
        METH_VARARGS,
        "Create spring image named outName from imgName image"
    },
    {
        "create_winter",
        create_winter,
        //METH_NOARGS,
        METH_VARARGS,
        "Create winter image named outName from imgName image"
    },
    {NULL, NULL, 0, NULL}
};

// Module definition
// The arguments of this structure tell Python what to call your extension,
// what it's methods are and where to look for it's method definitions
static struct PyModuleDef fast_image_mask_definition = { 
    PyModuleDef_HEAD_INIT,
    "fast_image_mask",
    "Image masking from C so it is not horrendously slow",
    -1, 
    fast_image_mask_functions
};

// Module initialization
// Python calls this function when importing your extension. It is important
// that this function is named PyInit_[[your_module_name]] exactly, and matches
// the name keyword argument in setup.py's setup() call.
PyMODINIT_FUNC PyInit_fast_image_mask(void) {
    Py_Initialize();

    return PyModule_Create(&fast_image_mask_definition);
}

