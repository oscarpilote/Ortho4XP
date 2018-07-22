#include <Python.h>
#include <iostream>
#include <Magick++.h>

using namespace std;
using namespace Magick;

void foreach_pixel(Image *img, void (*callback)(Quantum *)) {
    img->modifyImage();
    // Allocate pixel view
    Pixels view(*img);

    // Set all pixels in region anchored at 38x36, with size 160x230 to green.
    size_t columns = img->columns();
    size_t rows = img->rows();
    Quantum *pixels = view.get(0, 0, columns, rows);
    unsigned long long total = 0;
    for (ssize_t row = 0; row < rows; row++) {
        for (ssize_t column = 0; column < columns; column++) {
            unsigned int offset = img->channels() * (columns * row + column);
            (*callback)(pixels + offset);
        }
    }

    // Save changes to image.
    view.sync();
}

void create_night_mask(Image *img) {
    foreach_pixel(img,
        [](Quantum *pixel) {
            Quantum red = pixel[0];
            Quantum green = pixel[1];
            Quantum blue = pixel[2];
            cout << "[" << red << " " << green << " " << blue << "]" << endl;
        }
    );
}
// Comments and tutorial courtesy of http://adamlamers.com/post/NUBSPFQJ50J1
// Actual module method definition - this is the code that will be called by
// hello_module.print_hello_world
static PyObject * fast_image_mask_print_hello_world(PyObject *self, PyObject *args) {
    InitializeMagick("");

    // Construct the image object. Seperating image construction from the
    // the read operation ensures that a failure to read the image file
    // doesn't render the image object useless.
    Image image;
    try {
        // Read a file into image object
        image.read("TEST.bmp");
        create_night_mask(&image);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
        Py_RETURN_NONE;
    }

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
        "print_hello_world",
        fast_image_mask_print_hello_world,
        METH_NOARGS,
        "Print 'hello world' from a method defined in a C extension."
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

