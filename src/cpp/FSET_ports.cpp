#include <cmath>
#include "FSET_ports.h"
#include <Magick++.h>

using namespace Magick;
using namespace std;

bool pixelIsWaterOrWaterTransition(Quantum *pixel) {
    const Quantum BLUE_DIFF_THRESHOLD = 50;
    Quantum redDiff = abs(0 - pixel[0]);   
    Quantum greenDiff = abs(1 - pixel[1]);   
    Quantum blueDiff = abs(2 - pixel[2]);   

    if (((redDiff + greenDiff + blueDiff) / 3.0) <= BLUE_DIFF_THRESHOLD) {
        return true;
    }

    return false;
}

