#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <mesh_defs.h>
#include <mesh_io.h>

typedef struct {
    PyObject_HEAD
    Mesh cmesh;	    
} PyMesh;

static int py_initialize_mesh(PyMesh* self, PyObject *args, PyObject *kwds)
{
    initialize_mesh(&(self->cmesh));
    return 0;
}

static void py_dispose_mesh(PyMesh* self)
{
    dispose_mesh(&(self->cmesh));
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyTypeObject PyMeshType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "pymesh.mesh",
    .tp_doc = "Python mesh",
    .tp_basicsize = sizeof(PyMesh),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = py_initialize_mesh,
    .tp_dealloc = py_dispose_mesh,
};

static PyObject* py_read_mesh_from_mesh_file(PyObject* self, PyObject* args)
{
   int res;
   char* filename;
   PyMesh* pym;  
   if (!PyArg_ParseTuple(args, "Os", &pym, &filename))
	   return PyLong_FromLong(0);
   AffineT3 aff = {0, 0, 0, 1, 1, 1}; 
   dispose_mesh(&(pym->cmesh));
   res = read_mesh_from_mesh_file(&(pym->cmesh), &aff, filename);
   return PyLong_FromLong(res);
}

PyDoc_STRVAR(no_doc,"");

PyMethodDef pymesh_methods[] = {
    //{"dispose_mesh", (PyCFunction) py_dispose_mesh, METH_VARARGS, no_doc},
    {"read_mesh_from_mesh_file", (PyCFunction) py_read_mesh_from_mesh_file, METH_VARARGS, no_doc},
    {NULL},
};

static PyModuleDef PyMeshModule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "pymesh",
    .m_doc = "Example module that allows to access meshes.",
    .m_size = -1,
    .m_methods = pymesh_methods,
};

PyMODINIT_FUNC
PyInit_pymesh(void)
{
    PyObject *m;
    if (PyType_Ready(&PyMeshType) < 0)
        return NULL;

    m = PyModule_Create(&PyMeshModule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&PyMeshType);
    PyModule_AddObject(m, "PyMesh", (PyObject *) &PyMeshType);
    return m;
}
