/* Example of Python c module with an invalid __text_signature__  */

#include "Python.h"

static PyObject* base_valid(PyObject *self, PyObject* args)
{
    printf("Hello World\n");
    return Py_None;
}

static PyObject* base_invalid(PyObject *self, PyObject* args)
{
    printf("Hello World\n");
    return Py_None;
}

static PyMethodDef base_methods[] = {
    {"valid_text_signature",             base_valid,      METH_VARARGS,   "valid_text_signature($self, a='r', b=-3.14)\n"
    "--\n"
    "\n"
    "Function demonstrating a valid __text_signature__ from C code."},

    {"invalid_text_signature",             base_invalid,      METH_VARARGS,   "invalid_text_signature(!invalid) -> NotSupported\n"
    "--\n"
    "\n"
    "Function demonstrating an invalid __text_signature__ from C code."},
    
    {NULL,              NULL,           0,              NULL}           /* sentinel */
};

static PyModuleDef base_definition = {
    PyModuleDef_HEAD_INIT,
    "base",
    "A Python module demonstrating valid and invalid __text_signature__ from C code.",
    -1,
    base_methods
};

PyObject* PyInit_base(void) {
    Py_Initialize();
    return PyModule_Create(&base_definition);
}
