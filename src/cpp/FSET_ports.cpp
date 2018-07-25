#include <cmath>
#include "FSET_ports.h"
#include <Magick++.h>
#include <string>
#include <iostream>

using namespace Magick;
using namespace std;

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

void c_create_night(string imgName, string outName) {
    try {
        Image img;
        img.read(imgName);
        foreach_pixel(&img,
            [](Quantum *pixel) {
                Quantum vRed = pixel[0];
                Quantum vGreen = pixel[1];
                Quantum vBlue = pixel[2];

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
    }
}
void c_create_hard_winter(string imgName, string outName) {
    try {
        Image img;
        img.read(imgName);
        foreach_pixel(&img,
            [](Quantum *pixel) {
                Quantum vRed = pixel[0];
                Quantum vGreen = pixel[1];
                Quantum vBlue = pixel[2];

                bool vIsWater = pixelIsWaterOrWaterTransition(pixel);
                bool vStreets = true;
                ssize_t vSum = vRed + vGreen + vBlue;
                bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && vIsWater;
                bool vSnowAllowed    = !(MasksConfig::mNoSnowInWaterForWinterAndHardWinter && vIsWater);

                if (!vDontAlterColor) {
                    vSum = vRed + vGreen + vBlue;

                    if (MasksConfig::mHardWinterStreetsConditionOn &&
                         ((vRed - vBlue)   < MasksConfig::mHardWinterStreetConditionGreyToleranceValue) && ((vRed - vBlue)   > -MasksConfig::mHardWinterStreetConditionGreyToleranceValue) &&
                         ((vRed - vGreen)  < MasksConfig::mHardWinterStreetConditionGreyToleranceValue) && ((vRed - vGreen)  > -MasksConfig::mHardWinterStreetConditionGreyToleranceValue) &&
                         ((vGreen - vBlue) < MasksConfig::mHardWinterStreetConditionGreyToleranceValue) && ((vGreen - vBlue) > -MasksConfig::mHardWinterStreetConditionGreyToleranceValue) &&
                         (vSum > MasksConfig::mHardWinterStreetConditionRGBSumLargerThanValue) &&
                         (vSum < MasksConfig::mHardWinterStreetConditionRGBSumLessThanValue)) {
                        Quantum vAverage = ((Quantum)(vSum)) / 3.0f;
                        vRed   = (Quantum)(MasksConfig::mHardWinterStreetAverageFactor * (vAverage + ((Quantum)(rand()) * MasksConfig::mHardWinterStreetAverageAdditionRandomFactor + MasksConfig::mHardWinterStreetAverageAdditionRandomOffset)) + MasksConfig::mHardWinterStreetAverageRedOffset);
                        vGreen = (Quantum)(MasksConfig::mHardWinterStreetAverageFactor * (vAverage + ((Quantum)(rand()) * MasksConfig::mHardWinterStreetAverageAdditionRandomFactor + MasksConfig::mHardWinterStreetAverageAdditionRandomOffset)) + MasksConfig::mHardWinterStreetAverageGreenOffset);
                        vBlue  = (Quantum)(MasksConfig::mHardWinterStreetAverageFactor * (vAverage + ((Quantum)(rand()) * MasksConfig::mHardWinterStreetAverageAdditionRandomFactor + MasksConfig::mHardWinterStreetAverageAdditionRandomOffset)) + MasksConfig::mHardWinterStreetAverageBlueOffset);
                    } else if (vSum < MasksConfig::mHardWinterDarkConditionRGBSumLessThanValue) {
                        // If it is very dark(-green), it might be forest or very steep rock.
                        // In this case, we might want to sprinkle some more white pixels
                        // into that area every now and then:
                        if ( vSnowAllowed &&
                            (vGreen > (vRed - MasksConfig::mHardWinterDarkConditionRGDiffValue)) &&
                            (vGreen > vBlue) &&
                            (rand() < MasksConfig::mHardWinterDarkConditionRandomLessThanValue)) {
                            vRed   = MasksConfig::mHardWinterDarkRedOffset   + (Quantum)(((Quantum)(rand()) * MasksConfig::mHardWinterDarkRandomFactor));
                            vGreen = MasksConfig::mHardWinterDarkGreenOffset + (Quantum)(((Quantum)(rand()) * MasksConfig::mHardWinterDarkRandomFactor));
                            vBlue  = MasksConfig::mHardWinterDarkBlueOffset  + (Quantum)(((Quantum)(rand()) * MasksConfig::mHardWinterDarkRandomFactor));
                        } else {
                            // leave very dark pixel (basically) unchanged:
                            if (vStreets) {
                                vRed   = (Quantum)(MasksConfig::mHardWinterVeryDarkStreetFactor * (Quantum)(vRed));
                                vGreen = (Quantum)(MasksConfig::mHardWinterVeryDarkStreetFactor * (Quantum)(vGreen));
                                vBlue  = (Quantum)(MasksConfig::mHardWinterVeryDarkStreetFactor * (Quantum)(vBlue));
                            } else {
                                vRed   = (Quantum)(MasksConfig::mHardWinterVeryDarkNormalFactor * (Quantum)(vRed));
                                vGreen = (Quantum)(MasksConfig::mHardWinterVeryDarkNormalFactor * (Quantum)(vGreen));
                                vBlue  = (Quantum)(MasksConfig::mHardWinterVeryDarkNormalFactor * (Quantum)(vBlue));
                            }
                        }
                    } else if (vSum >= MasksConfig::mHardWinterAlmostWhiteConditionRGBSumLargerEqualThanValue) {
                        // Almost white already, make it still whiter with a touch of blue:
                        if (vSum <= MasksConfig::mHardWinterAlmostWhiteConditionRGBSumLessEqualThanValue) {
                            vRed = (Quantum)(MasksConfig::mHardWinterAlmostWhiteRedFactor * (Quantum)(vRed));
                            vGreen = (Quantum)(MasksConfig::mHardWinterAlmostWhiteGreenFactor * (Quantum)(vGreen));
                            vBlue = (Quantum)(MasksConfig::mHardWinterAlmostWhiteBlueFactor * (Quantum)(vBlue));
                        }
                    } else {
                        // Let the dominating color shine through
                        // For some funny reason, green pixel may be dominated by red color...
                        if (vSnowAllowed &&
                            ((vRed - MasksConfig::mHardWinterRestConditionRGDiffValue) > vGreen) &&
                            (vRed > vBlue)) {
                            // maybe red-12 / red-8 or something like this to distinguish between
                            // wi and hw in lower areas...
                            if (vRed < MasksConfig::mHardWinterRestRedMin) {
                                vRed = MasksConfig::mHardWinterRestRedMin;
                            }
                            vGreen = vRed + MasksConfig::mHardWinterRestGBOffsetToRed;
                            vBlue = vRed + MasksConfig::mHardWinterRestGBOffsetToRed;
                        } else if ((vGreen >= (vRed - MasksConfig::mHardWinterRestCondition2RGDiffValue)) &&
                                 (vGreen >= vBlue)) {
                            if (!vSnowAllowed ||
                                (vSum < MasksConfig::mHardWinterRestForestConditionRGBSumLessThan)) {  //0xF0
                                // Probably forest...
                                vGreen += MasksConfig::mHardWinterRestForestGreenOffset;
                            } else {
                                if (vGreen < MasksConfig::mHardWinterRestNonForestGreenLimit) {
                                    vGreen = MasksConfig::mHardWinterRestNonForestGreenLimit;
                                }
                                vRed = vGreen + MasksConfig::mHardWinterRestNonForestRedOffsetToGreen;
                                vBlue = vGreen + MasksConfig::mHardWinterRestNonForestBlueOffsetToGreen;
                            }
                        } else {  // if (blue >= red && blue > green)
                            if (vSnowAllowed) {
                                if (vBlue < MasksConfig::mHardWinterRestRestBlueMin) {
                                    vBlue = MasksConfig::mHardWinterRestRestBlueMin;
                                }
                                vRed = vBlue + MasksConfig::mHardWinterRestRestRGToBlueOffset;
                                vGreen = vBlue + MasksConfig::mHardWinterRestRestRGToBlueOffset;
                            }
                        }

                    }
                }
                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        img.write(outName);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_autumn(string imgName, string outName) {
    try {
        Image img;
        img.read(imgName);
        foreach_pixel(&img,
            [](Quantum *pixel) {
                Quantum vRed = pixel[0];
                Quantum vGreen = pixel[1];
                Quantum vBlue = pixel[2];

                bool vIsWater = pixelIsWaterOrWaterTransition(pixel);
                ssize_t vSum = vRed + vGreen + vBlue;
				bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && pixelIsWaterOrWaterTransition(pixel);

                if (!vDontAlterColor) {
                    vSum = vRed + vGreen + vBlue;

                    // Convert to autumn colors. Reduce green in all
                    // colors; reduce red in similar way, when the pixel
                    // is very bright; make red and blue brighter without
                    // touching green, when the pixel is rather dark

                    if ((vSum < MasksConfig::mAutumnDarkConditionRGBSumLessThanValue) &&
                        (vSum > MasksConfig::mAutumnDarkConditionRGBSumLargerThanValue)) {
                        // Dark pixel, but not black:
                        vRed   += MasksConfig::mAutumnDarkRedAddition;
                        vGreen += MasksConfig::mAutumnDarkGreenAddition;
                        vBlue  += MasksConfig::mAutumnDarkBlueAddition;
                    } else if ((vSum >= MasksConfig::mAutumnBrightConditionRGBSumLargerEqualThanValue) &&
                             (vSum < MasksConfig::mAutumnBrightConditionRGBSumLessThanValue)) {
                        //rather bright pixel
                        vRed   += MasksConfig::mAutumnBrightRedAddition;
                        vGreen += MasksConfig::mAutumnBrightGreenAddition;
                        vBlue  += MasksConfig::mAutumnBrightBlueAddition;
                    } else if ((MasksConfig::mAutumnGreenishConditionBlueIntegerFactor * vBlue) < (MasksConfig::mAutumnGreenishConditionGreenIntegerFactor * vGreen)) {  //1.4*blue < Green
                        //very greenish pixel
                        vRed   += MasksConfig::mAutumnGreenishRedAddition;
                        vGreen += MasksConfig::mAutumnGreenishGreenAddition;
                        vBlue  += MasksConfig::mAutumnGreenishBlueAddition;
                    } else {
                        vRed   += MasksConfig::mAutumnRestRedAddition;
                        vGreen += MasksConfig::mAutumnRestGreenAddition;
                        vBlue  += MasksConfig::mAutumnRestBlueAddition;
                    }
                }
                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        img.write(outName);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_spring(string imgName, string outName) {
    try {
        Image img;
        img.read(imgName);
        foreach_pixel(&img,
            [](Quantum *pixel) {
                Quantum vRed = pixel[0];
                Quantum vGreen = pixel[1];
                Quantum vBlue = pixel[2];

                ssize_t vSum = vRed + vGreen + vBlue;

                bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && pixelIsWaterOrWaterTransition(pixel);

                if (!vDontAlterColor) {
                    vSum = vRed + vGreen + vBlue;

                    if ((vSum < MasksConfig::mSpringDarkConditionRGBSumLessThanValue) &&
                        (vSum > MasksConfig::mSpringDarkConditionRGBSumLargerThanValue)) {
                        // Dark pixel, but not black:
                        vRed   += MasksConfig::mSpringDarkRedAddition;
                        vGreen += MasksConfig::mSpringDarkGreenAddition;
                        vBlue  += MasksConfig::mSpringDarkBlueAddition;
                    } else if ((vSum >= MasksConfig::mSpringBrightConditionRGBSumLargerEqualThanValue) &&
                             (vSum < MasksConfig::mSpringBrightConditionRGBSumLessThanValue)) {
                        //rather bright pixel
                        vRed   += MasksConfig::mSpringBrightRedAddition;
                        vGreen += MasksConfig::mSpringBrightGreenAddition;
                        vBlue  += MasksConfig::mSpringBrightBlueAddition;
                    } else if ((MasksConfig::mSpringGreenishConditionBlueIntegerFactor * vBlue) < (MasksConfig::mSpringGreenishConditionGreenIntegerFactor * vGreen)) {  //1.4*blue < Green
                        //very greenish pixel
                        vRed   += MasksConfig::mSpringGreenishRedAddition;
                        vGreen += MasksConfig::mSpringGreenishGreenAddition;
                        vBlue  += MasksConfig::mSpringGreenishBlueAddition;
                    } else {
                        vRed   += MasksConfig::mSpringRestRedAddition;
                        vGreen += MasksConfig::mSpringRestGreenAddition;
                        vBlue  += MasksConfig::mSpringRestBlueAddition;
                    }
                }
                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        img.write(outName);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_winter(string imgName, string outName) {
    try {
        Image img;
        img.read(imgName);
        foreach_pixel(&img,
            [](Quantum *pixel) {
                Quantum vRed = pixel[0];
                Quantum vGreen = pixel[1];
                Quantum vBlue = pixel[2];

                ssize_t vSum = vRed + vGreen + vBlue;

                bool vIsWater = pixelIsWaterOrWaterTransition(pixel);
                bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && vIsWater;
                //bool vSnowAllowed    = !(MasksConfig::mNoSnowInWaterForWinterAndHardWinter && vIsWater);

                if (!vDontAlterColor) {
                    vSum = vRed + vGreen + vBlue;

                    // Basically fall routines with snow on greyish fields and streets:
                    if (((vRed - vBlue)   < MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) && ((vRed - vBlue)   > -MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) &&
                        ((vRed - vGreen)  < MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) && ((vRed - vGreen)  > -MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) &&
                        ((vGreen - vBlue) < MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) && ((vGreen - vBlue) > -MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) &&
                         (vSum > MasksConfig::mWinterStreetGreyConditionRGBSumLargerThanValue)) {
                        Quantum vMax = vRed;
                        if (vGreen > vMax) {
                            vMax = vGreen;
                        }
                        if (vBlue > vMax) {
                            vMax = vBlue;
                        }
                        Quantum vMaxDouble = MasksConfig::mWinterStreetGreyMaxFactor * (Quantum)(vMax);
                        vRed   = (Quantum)(((Quantum)(rand()) * MasksConfig::mWinterStreetGreyRandomFactor + vMax));
                        vGreen = (Quantum)(((Quantum)(rand()) * MasksConfig::mWinterStreetGreyRandomFactor + vMax));
                        vBlue  = (Quantum)(((Quantum)(rand()) * MasksConfig::mWinterStreetGreyRandomFactor + vMax));
                    } else if ((vSum < MasksConfig::mWinterDarkConditionRGBSumLessThanValue) &&
                             (vSum > MasksConfig::mWinterDarkConditionRGBSumLargerThanValue)) {
                        // Rather dark pixel, but not black
                        vRed   += MasksConfig::mWinterDarkRedAddition;
                        vGreen += MasksConfig::mWinterDarkGreenAddition;
                        vBlue  += MasksConfig::mWinterDarkBlueAddition;
                    } else if ((vSum >= MasksConfig::mWinterBrightConditionRGBSumLargerEqualThanValue) &&
                             (vSum < MasksConfig::mWinterBrightConditionRGBSumLessThanValue)) {
                        // rather bright pixel
                        vRed   += MasksConfig::mWinterBrightRedAddition;
                        vGreen += MasksConfig::mWinterBrightGreenAddition;
                        vBlue  += MasksConfig::mWinterBrightBlueAddition;
                    } else if ((MasksConfig::mWinterGreenishConditionBlueIntegerFactor * vBlue) < (MasksConfig::mWinterGreenishConditionGreenIntegerFactor * vGreen)) {  //1.4*blue < Green
                        //very greenish pixel
                        vRed   += MasksConfig::mWinterGreenishRedAddition;
                        vGreen += MasksConfig::mWinterGreenishGreenAddition;
                        vBlue  += MasksConfig::mWinterGreenishBlueAddition;
                    } else {
                        vRed   += MasksConfig::mWinterRestRedAddition;
                        vGreen += MasksConfig::mWinterRestGreenAddition;
                        vBlue  += MasksConfig::mWinterRestBlueAddition;
                    }
                }
                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        img.write(outName);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}

