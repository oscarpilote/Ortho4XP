#include <Python.h>
#include <iostream>
#include <Magick++.h>
#include "FSET_ports.h"
#include <string>

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
    for (ssize_t row = 0; row < rows; row++) {
        for (ssize_t column = 0; column < columns; column++) {
            unsigned int offset = img->channels() * (columns * row + column);
            (*callback)(pixels + offset);
        }
    }

    // Save changes to image.
    view.sync();
}

void create_night_mask(string imgName, string outName) {
}
// Comments and tutorial courtesy of http://adamlamers.com/post/NUBSPFQJ50J1
// Actual module method definition - this is the code that will be called by
// hello_module.print_hello_world
static PyObject * create_night_mask(PyObject *self, PyObject *args) {
    InitializeMagick("");
    const char *imgName, *outName;
    if (!PyArg_ParseTuple(args, "ss", &imgName, &outName)) {
        return NULL;
    }

    try {
        Image img;
        img.read(imgName);
        foreach_pixel(&img,
            [](Quantum *pixel) {
                Quantum vRed = pixel[0];
                Quantum vGreen = pixel[1];
                Quantum vBlue = pixel[2];

                // TODO: placeholder, need logic for this later
                bool vIsWater = pixelIsWaterOrWaterTransition(pixel);
                ssize_t vSum = vRed + vGreen + vBlue;

                if ((!vIsWater) &&
                    ((vRed - vBlue)   < MasksConfig::mNightStreetGreyConditionGreyToleranceValue) && ((vRed - vBlue)   > -MasksConfig::mNightStreetGreyConditionGreyToleranceValue) &&
                    ((vRed - vGreen)  < MasksConfig::mNightStreetGreyConditionGreyToleranceValue) && ((vRed - vGreen)  > -MasksConfig::mNightStreetGreyConditionGreyToleranceValue) &&
                    ((vGreen - vBlue) < MasksConfig::mNightStreetGreyConditionGreyToleranceValue) && ((vGreen - vBlue) > -MasksConfig::mNightStreetGreyConditionGreyToleranceValue) &&
                    (vSum  > MasksConfig::mNightStreetConditionRGBSumLargerThanValue) &&
                    (vSum <= MasksConfig::mNightStreetConditionRGBSumLessEqualThanValue)) {
                    //Stree random dither lights
                    if (rand() < MasksConfig::mNightStreetLightDots1DitherProbabily) {
                        vRed   = MasksConfig::mNightStreetLightDot1Red;
                        vGreen = MasksConfig::mNightStreetLightDot1Green;
                        vBlue  = MasksConfig::mNightStreetLightDot1Blue;
                    } else if (rand() < MasksConfig::mNightStreetLightDots2DitherProbabily) {
                        vRed   = MasksConfig::mNightStreetLightDot2Red;
                        vGreen = MasksConfig::mNightStreetLightDot2Green;
                        vBlue  = MasksConfig::mNightStreetLightDot2Blue;
                    } else if (rand() < MasksConfig::mNightStreetLightDots3DitherProbabily) {
                        vRed   = MasksConfig::mNightStreetLightDot3Red;
                        vGreen = MasksConfig::mNightStreetLightDot3Green;
                        vBlue  = MasksConfig::mNightStreetLightDot3Blue;
                    } else {
                        //Street Make bright and orange
                        vRed   += MasksConfig::mNightStreetRedAddition;
                        vGreen += MasksConfig::mNightStreetGreenAddition;
                        vBlue  += MasksConfig::mNightStreetBlueAddition;
                    }
                } else {
                    //Normal Land/Water...make factor 2 darker
                    vRed   = (Quantum) MasksConfig::mNightNonStreetLightness * vRed;
                    vGreen = (Quantum) MasksConfig::mNightNonStreetLightness * vGreen;
                    vBlue  = (Quantum) MasksConfig::mNightNonStreetLightness * vBlue;
                }
                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        img.write(outName);
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
        "create_night_mask",
        create_night_mask,
        //METH_NOARGS,
        METH_VARARGS,
        "Create night mask image named outName from imgName image"
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

