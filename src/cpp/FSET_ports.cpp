#include <cmath>
#include "FSET_ports.h"
#include <Magick++.h>
#include <string>
#include <iostream>

using namespace Magick;
using namespace std;

static double nextDouble(double min, double max) {
    double f = (double) rand() / RAND_MAX;

    return min + f * (max - min);
}

static void limitRGBValues(int32_t *xRed, int32_t *xGreen, int32_t *xBlue) {
    if (*xRed > (int) UCHAR_MAX) {
        *xRed = (int) UCHAR_MAX;
    } else if (*xRed < 0) {
        *xRed = 0;
    }
    if (*xGreen > (int) UCHAR_MAX) {
        *xGreen = (int) UCHAR_MAX;
    } else if (*xGreen < 0) {
        *xGreen = 0;
    }
    if (*xBlue > (int) UCHAR_MAX) {
        *xBlue = (int) UCHAR_MAX;
    } else {
        if (*xBlue >= 0) {
          return;
        }
      *xBlue = 0;
    }
}

void foreach_pixel(Image *img, std::function<void(Quantum *, ssize_t, ssize_t)> callback) {
    img->modifyImage();
    // Allocate pixel view
    Pixels view(*img);
    // Set all pixels in region anchored at 0x0, with size rowsxcolumns to green.
    size_t columns = img->columns();
    size_t rows = img->rows();
    Quantum *pixels = view.get(0, 0, columns, rows);
    for (ssize_t row = 0; row < rows; row++) {
        for (ssize_t column = 0; column < columns; column++) {
            unsigned int offset = img->channels() * (columns * row + column);
            callback(pixels + offset, column, row);
        }
    }

    // Save changes to image.
    view.sync();
}

static Quantum * getPixel(Image *img, Quantum *pixels, ssize_t x, ssize_t y) {
    size_t columns = img->columns();
    unsigned int offset = img->channels() * (columns * y + x);

    return (pixels + offset);
}

bool fileExists(char *fileName) {
    if (!fileName) {
        return false;
    }

    FILE *file = fopen(fileName, "r");
    bool exists = false;
    if (file) {
        exists = true;
        fclose(file);
    }

    return exists;
}

WaterPixelChecker::WaterPixelChecker(char *mask_img_path) {
    this->setMaskAndGetGetPixels(mask_img_path);
}

WaterPixelChecker::~WaterPixelChecker() {
    if (pixelsView) {
        delete pixelsView;
        pixelsView = NULL;
    }
}

Quantum * WaterPixelChecker::getPixels(Image *img) {
    if (pixelsView) {
        delete pixelsView;
        pixelsView = NULL;
    }
    // Allocate pixel view
    pixelsView = new Pixels(*img);
    // Set all pixels in region anchored at 0x0, with size rowsxcolumns to green.
    size_t columns = img->columns();
    size_t rows = img->rows();
    // these pixels are handled by view and won't be dealloced until view is...
    Quantum *pixels = pixelsView->get(0, 0, columns, rows);

    return pixels;
}

void WaterPixelChecker::setMaskAndGetGetPixels(char *mask_img_path) {
    this->mask_img_path = mask_img_path;
    maskFileExists = fileExists(mask_img_path);
    if (maskFileExists) {
        Image img;
        img.read(mask_img_path);
        imgColumns = img.columns();
        imgChannels = img.channels();
        pixels = getPixels(&img);
    }
}

// FSET uses Area.kml, we use water mask tiff file
bool WaterPixelChecker::pixelIsWaterOrWaterTransition(ssize_t x, ssize_t y) {
    if (!mask_img_path) {
        return false;
    }
    if (!maskFileExists) {
        return false;
    }
    unsigned int offset = imgChannels * (imgColumns * y + x);
    Quantum *pixel = (pixels + offset);
    int32_t red = pixel[0];
    int32_t green = pixel[1];
    int32_t blue = pixel[2];

    // all black pixel == water
    if (red == 0 && green == 0 && blue == 0) {
        return true;
    }

    return false;
}

RandomNumberGenerator::RandomNumberGenerator():gen(this->rd()) {}

double RandomNumberGenerator::nextDouble() {
    return this->dis(this->gen);
}

// the below functions are ports from FSET night/season creation scripts
void c_create_night(char *imgName, char *outName, char *mask_img_path) {
    try {
        Image img;
        img.read(imgName);
        WaterPixelChecker pixelChecker(mask_img_path);
        RandomNumberGenerator random;

        foreach_pixel(&img,
            [&pixelChecker, &random](Quantum *pixel, ssize_t x, ssize_t y) {
                int32_t vRed = (int32_t) pixel[0];
                int32_t vGreen = (int32_t) pixel[1];
                int32_t vBlue = (int32_t) pixel[2];

                bool vIsWater = pixelChecker.pixelIsWaterOrWaterTransition(x, y);
                ssize_t vSum = vRed + vGreen + vBlue;

                if ((!vIsWater) &&
                    ((vRed - vBlue)   < MasksConfig::mNightStreetGreyConditionGreyToleranceValue) && ((vRed - vBlue)   > -MasksConfig::mNightStreetGreyConditionGreyToleranceValue) &&
                    ((vRed - vGreen)  < MasksConfig::mNightStreetGreyConditionGreyToleranceValue) && ((vRed - vGreen)  > -MasksConfig::mNightStreetGreyConditionGreyToleranceValue) &&
                    ((vGreen - vBlue) < MasksConfig::mNightStreetGreyConditionGreyToleranceValue) && ((vGreen - vBlue) > -MasksConfig::mNightStreetGreyConditionGreyToleranceValue) &&
                    (vSum  > MasksConfig::mNightStreetConditionRGBSumLargerThanValue) &&
                    (vSum <= MasksConfig::mNightStreetConditionRGBSumLessEqualThanValue)) {
                    //Stree random dither lights
                    if (random.nextDouble() < MasksConfig::mNightStreetLightDots1DitherProbabily) {
                        vRed   = MasksConfig::mNightStreetLightDot1Red;
                        vGreen = MasksConfig::mNightStreetLightDot1Green;
                        vBlue  = MasksConfig::mNightStreetLightDot1Blue;
                    } else if (random.nextDouble() < MasksConfig::mNightStreetLightDots2DitherProbabily) {
                        vRed   = MasksConfig::mNightStreetLightDot2Red;
                        vGreen = MasksConfig::mNightStreetLightDot2Green;
                        vBlue  = MasksConfig::mNightStreetLightDot2Blue;
                    } else if (random.nextDouble() < MasksConfig::mNightStreetLightDots3DitherProbabily) {
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
                    vRed   = (int32_t) (MasksConfig::mNightNonStreetLightness * ((float) vRed));
                    vGreen = (int32_t) (MasksConfig::mNightNonStreetLightness * ((float) vGreen));
                    vBlue  = (int32_t) (MasksConfig::mNightNonStreetLightness * ((float) vBlue));
                }
                limitRGBValues(&vRed, &vGreen, &vBlue);

                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        string outString(outName);
        outString = "BMP3:" + outString;
        img.write(outString);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_hard_winter(char *imgName, char *outName, char *mask_img_path) {
    try {
        Image img;
        img.read(imgName);
        WaterPixelChecker pixelChecker(mask_img_path);
        RandomNumberGenerator random;

        foreach_pixel(&img,
            [&pixelChecker, &random](Quantum *pixel, ssize_t x, ssize_t y) {
                int32_t vRed = (int32_t) pixel[0];
                int32_t vGreen = (int32_t) pixel[1];
                int32_t vBlue = (int32_t) pixel[2];

                bool vIsWater = pixelChecker.pixelIsWaterOrWaterTransition(x, y);
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
                        float vAverage = ((Quantum)(vSum)) / 3.0f;
                        vRed   = (int32_t) (MasksConfig::mHardWinterStreetAverageFactor * (vAverage + ((float) (random.nextDouble()) * MasksConfig::mHardWinterStreetAverageAdditionRandomFactor + MasksConfig::mHardWinterStreetAverageAdditionRandomOffset)) + MasksConfig::mHardWinterStreetAverageRedOffset);
                        vGreen = (int32_t) (MasksConfig::mHardWinterStreetAverageFactor * (vAverage + ((float) (random.nextDouble()) * MasksConfig::mHardWinterStreetAverageAdditionRandomFactor + MasksConfig::mHardWinterStreetAverageAdditionRandomOffset)) + MasksConfig::mHardWinterStreetAverageGreenOffset);
                        vBlue  = (int32_t) (MasksConfig::mHardWinterStreetAverageFactor * (vAverage + ((float) (random.nextDouble()) * MasksConfig::mHardWinterStreetAverageAdditionRandomFactor + MasksConfig::mHardWinterStreetAverageAdditionRandomOffset)) + MasksConfig::mHardWinterStreetAverageBlueOffset);
                    } else if (vSum < MasksConfig::mHardWinterDarkConditionRGBSumLessThanValue) {
                        // If it is very dark(-green), it might be forest or very steep rock.
                        // In this case, we might want to sprinkle some more white pixels
                        // into that area every now and then:
                        if ( vSnowAllowed &&
                            (vGreen > (vRed - MasksConfig::mHardWinterDarkConditionRGDiffValue)) &&
                            (vGreen > vBlue) &&
                            (random.nextDouble() < MasksConfig::mHardWinterDarkConditionRandomLessThanValue)) {
                            vRed   = MasksConfig::mHardWinterDarkRedOffset   + (int32_t) (((float) (random.nextDouble()) * MasksConfig::mHardWinterDarkRandomFactor));
                            vGreen = MasksConfig::mHardWinterDarkGreenOffset + (int32_t) (((float) (random.nextDouble()) * MasksConfig::mHardWinterDarkRandomFactor));
                            vBlue  = MasksConfig::mHardWinterDarkBlueOffset  + (int32_t) (((float) (random.nextDouble()) * MasksConfig::mHardWinterDarkRandomFactor));
                        } else {
                            // leave very dark pixel (basically) unchanged:
                            if (vStreets) {
                                vRed   = (int32_t) (MasksConfig::mHardWinterVeryDarkStreetFactor * (float) (vRed));
                                vGreen = (int32_t) (MasksConfig::mHardWinterVeryDarkStreetFactor * (float) (vGreen));
                                vBlue  = (int32_t) (MasksConfig::mHardWinterVeryDarkStreetFactor * (float) (vBlue));
                            } else {
                                vRed   = (int32_t) (MasksConfig::mHardWinterVeryDarkNormalFactor * (float) (vRed));
                                vGreen = (int32_t) (MasksConfig::mHardWinterVeryDarkNormalFactor * (float) (vGreen));
                                vBlue  = (int32_t) (MasksConfig::mHardWinterVeryDarkNormalFactor * (float) (vBlue));
                            }
                        }
                    } else if (vSum >= MasksConfig::mHardWinterAlmostWhiteConditionRGBSumLargerEqualThanValue) {
                        // Almost white already, make it still whiter with a touch of blue:
                        if (vSum <= MasksConfig::mHardWinterAlmostWhiteConditionRGBSumLessEqualThanValue) {
                            vRed = (int32_t) (MasksConfig::mHardWinterAlmostWhiteRedFactor * (float) (vRed));
                            vGreen = (int32_t) (MasksConfig::mHardWinterAlmostWhiteGreenFactor * (float) (vGreen));
                            vBlue = (int32_t) (MasksConfig::mHardWinterAlmostWhiteBlueFactor * (float) (vBlue));
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
                limitRGBValues(&vRed, &vGreen, &vBlue);

                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        string outString(outName);
        outString = "BMP3:" + outString;
        img.write(outString);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_autumn(char *imgName, char *outName, char *mask_img_path) {
    try {
        Image img;
        img.read(imgName);
        WaterPixelChecker pixelChecker(mask_img_path);
        RandomNumberGenerator random;

        foreach_pixel(&img,
            [&pixelChecker, &random](Quantum *pixel, ssize_t x, ssize_t y) {
                int32_t vRed = (int32_t) pixel[0];
                int32_t vGreen = (int32_t) pixel[1];
                int32_t vBlue = (int32_t) pixel[2];

                ssize_t vSum = vRed + vGreen + vBlue;
                bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && pixelChecker.pixelIsWaterOrWaterTransition(x, y);

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
                limitRGBValues(&vRed, &vGreen, &vBlue);

                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        string outString(outName);
        outString = "BMP3:" + outString;
        img.write(outString);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_spring(char *imgName, char *outName, char *mask_img_path) {
    try {
        Image img;
        img.read(imgName);
        WaterPixelChecker pixelChecker(mask_img_path);
        RandomNumberGenerator random;

        foreach_pixel(&img,
            [&pixelChecker, &random](Quantum *pixel, ssize_t x, ssize_t y) {
                int32_t vRed = (int32_t) pixel[0];
                int32_t vGreen = (int32_t) pixel[1];
                int32_t vBlue = (int32_t) pixel[2];

                ssize_t vSum = vRed + vGreen + vBlue;

                bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && pixelChecker.pixelIsWaterOrWaterTransition(x, y);

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
                limitRGBValues(&vRed, &vGreen, &vBlue);

                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        string outString(outName);
        outString = "BMP3:" + outString;
        img.write(outString);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
void c_create_winter(char *imgName, char *outName, char *mask_img_path) {
    try {
        Image img;
        img.read(imgName);
        WaterPixelChecker pixelChecker(mask_img_path);
        RandomNumberGenerator random;

        foreach_pixel(&img,
            [&pixelChecker, &random](Quantum *pixel, ssize_t x, ssize_t y) {
                int32_t vRed = (int32_t) pixel[0];
                int32_t vGreen = (int32_t) pixel[1];
                int32_t vBlue = (int32_t) pixel[2];

                ssize_t vSum = vRed + vGreen + vBlue;

                bool vIsWater = pixelChecker.pixelIsWaterOrWaterTransition(x, y);
                bool vDontAlterColor = MasksConfig::mSpareOutWaterForSeasonsGeneration && vIsWater;
                //bool vSnowAllowed    = !(MasksConfig::mNoSnowInWaterForWinterAndHardWinter && vIsWater);

                if (!vDontAlterColor) {
                    vSum = vRed + vGreen + vBlue;

                    // Basically fall routines with snow on greyish fields and streets:
                    if (((vRed - vBlue)   < MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) && ((vRed - vBlue)   > -MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) &&
                        ((vRed - vGreen)  < MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) && ((vRed - vGreen)  > -MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) &&
                        ((vGreen - vBlue) < MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) && ((vGreen - vBlue) > -MasksConfig::mWinterStreetGreyConditionGreyToleranceValue) &&
                         (vSum > MasksConfig::mWinterStreetGreyConditionRGBSumLargerThanValue)) {
                        int32_t vMax = vRed;
                        if (vGreen > vMax) {
                            vMax = vGreen;
                        }
                        if (vBlue > vMax) {
                            vMax = vBlue;
                        }
                        float vMaxDouble = MasksConfig::mWinterStreetGreyMaxFactor * (float) (vMax);
                        vRed   = (int32_t) (((float) (random.nextDouble()) * MasksConfig::mWinterStreetGreyRandomFactor + vMax));
                        vGreen = (int32_t) (((float) (random.nextDouble()) * MasksConfig::mWinterStreetGreyRandomFactor + vMax));
                        vBlue  = (int32_t) (((float) (random.nextDouble()) * MasksConfig::mWinterStreetGreyRandomFactor + vMax));
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
                limitRGBValues(&vRed, &vGreen, &vBlue);

                pixel[0] = vRed;
                pixel[1] = vGreen;
                pixel[2] = vBlue;
            }
        );
        string outString(outName);
        outString = "BMP3:" + outString;
        img.write(outString);
    } catch(Exception &error_) {
        cout << "Caught exception: " << error_.what() << endl;
    }
}
