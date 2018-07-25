#ifndef FSET_MASKS_H
#define FSET_MASKS_H

#include <Magick++.h>
#include <climits>
#include <string>

using namespace Magick;
using namespace std;

class MasksConfig {
    public:
        static const int mHardWinterStreetConditionGreyToleranceValue = 31;
        static const int mHardWinterStreetConditionRGBSumLargerThanValue = 256;
        static const int mHardWinterStreetConditionRGBSumLessThanValue = 508;
        static constexpr float mHardWinterStreetAverageAdditionRandomFactor = 6;
        static constexpr float mHardWinterStreetAverageAdditionRandomOffset = -2;
        static constexpr float mHardWinterStreetAverageFactor = 0.9;
        static const int mHardWinterStreetAverageRedOffset = 0;
        static const int mHardWinterStreetAverageGreenOffset = 0;
        static const int mHardWinterStreetAverageBlueOffset = 10;
        static const int mHardWinterDarkConditionRGBSumLessThanValue = 96;
        static const int mHardWinterDarkConditionRGDiffValue = 12;
        static constexpr float mHardWinterDarkConditionRandomLessThanValue = 0.21;
        static constexpr float mHardWinterDarkRandomFactor = 11;
        static const int mHardWinterDarkRedOffset = 250;
        static const int mHardWinterDarkGreenOffset = 253;
        static const int mHardWinterDarkBlueOffset = 253;
        static constexpr float mHardWinterVeryDarkStreetFactor = 1.47;
        static constexpr float mHardWinterVeryDarkNormalFactor = 1.27;
        static const int mHardWinterAlmostWhiteConditionRGBSumLargerEqualThanValue = 608;
        static const int mHardWinterAlmostWhiteConditionRGBSumLessEqualThanValue = 752;
        static constexpr float mHardWinterAlmostWhiteRedFactor = 1.06;
        static constexpr float mHardWinterAlmostWhiteGreenFactor = 1.09;
        static constexpr float mHardWinterAlmostWhiteBlueFactor = 1.1;
        static const int mHardWinterRestConditionRGDiffValue = 10;
        static const int mHardWinterRestRedMin = 250;
        static const int mHardWinterRestGBOffsetToRed = -2;
        static const int mHardWinterRestCondition2RGDiffValue = 10;
        static const int mHardWinterRestForestConditionRGBSumLessThan = 240;
        static const int mHardWinterRestForestGreenOffset = -30;
        static const int mHardWinterRestNonForestGreenLimit = 250;
        static const int mHardWinterRestNonForestRedOffsetToGreen = -5;
        static const int mHardWinterRestNonForestBlueOffsetToGreen = -2;
        static const int mHardWinterRestRestBlueMin = 250;
        static const int mHardWinterRestRestRGToBlueOffset = -4;
        static const int mWinterStreetGreyConditionGreyToleranceValue = 47;
        static const int mWinterStreetGreyConditionRGBSumLargerThanValue = 256;
        static constexpr float mWinterStreetGreyMaxFactor = 1.4;
        static constexpr float mWinterStreetGreyRandomFactor = 11;
        static const int mWinterDarkConditionRGBSumLessThanValue = 288;
        static const int mWinterDarkConditionRGBSumLargerThanValue = 18;
        static const int mWinterDarkRedAddition = 4;
        static const int mWinterDarkGreenAddition = -11;
        static const int mWinterDarkBlueAddition = 3;
        static const int mWinterBrightConditionRGBSumLargerEqualThanValue = 288;
        static const int mWinterBrightConditionRGBSumLessThanValue = 752;
        static const int mWinterBrightRedAddition = -20;
        static const int mWinterBrightGreenAddition = -14;
        static const int mWinterBrightBlueAddition = -12;
        static const int mWinterGreenishConditionBlueIntegerFactor = 7;
        static const int mWinterGreenishConditionGreenIntegerFactor = 5;
        static const int mWinterGreenishRedAddition = -13;
        static const int mWinterGreenishGreenAddition = -25;
        static const int mWinterGreenishBlueAddition = 0;
        static const int mWinterRestRedAddition = 0;
        static const int mWinterRestGreenAddition = -12;
        static const int mWinterRestBlueAddition = 0;
        static const int mAutumnDarkConditionRGBSumLessThanValue = 288;
        static const int mAutumnDarkConditionRGBSumLargerThanValue = 18;
        static const int mAutumnDarkRedAddition = 9;
        static const int mAutumnDarkGreenAddition = -8;
        static const int mAutumnDarkBlueAddition = 8;
        static const int mAutumnBrightConditionRGBSumLargerEqualThanValue = 288;
        static const int mAutumnBrightConditionRGBSumLessThanValue = 752;
        static const int mAutumnBrightRedAddition = -16;
        static const int mAutumnBrightGreenAddition = -10;
        static const int mAutumnBrightBlueAddition = -7;
        static const int mAutumnGreenishConditionBlueIntegerFactor = 7;
        static const int mAutumnGreenishConditionGreenIntegerFactor = 5;
        static const int mAutumnGreenishRedAddition = -9;
        static const int mAutumnGreenishGreenAddition = -20;
        static const int mAutumnGreenishBlueAddition = 0;
        static const int mAutumnRestRedAddition = 0;
        static const int mAutumnRestGreenAddition = -16;
        static const int mAutumnRestBlueAddition = 0;
        static const int mSpringDarkConditionRGBSumLessThanValue = 288;
        static const int mSpringDarkConditionRGBSumLargerThanValue = 18;
        static const int mSpringDarkRedAddition = 9;
        static const int mSpringDarkGreenAddition = -8;
        static const int mSpringDarkBlueAddition = 8;
        static const int mSpringBrightConditionRGBSumLargerEqualThanValue = 288;
        static const int mSpringBrightConditionRGBSumLessThanValue = 752;
        static const int mSpringBrightRedAddition = 15;
        static const int mSpringBrightGreenAddition = 10;
        static const int mSpringBrightBlueAddition = -10;
        static const int mSpringGreenishConditionBlueIntegerFactor = 7;
        static const int mSpringGreenishConditionGreenIntegerFactor = 5;
        static const int mSpringGreenishRedAddition = 10;
        static const int mSpringGreenishGreenAddition = 5;
        static const int mSpringGreenishBlueAddition = -5;
        static const int mSpringRestRedAddition = 0;
        static const int mSpringRestGreenAddition = 0;
        static const int mSpringRestBlueAddition = 0;
        static const int mNightStreetGreyConditionGreyToleranceValue = 11;
        static const int mNightStreetConditionRGBSumLessEqualThanValue = 510;
        static const int mNightStreetConditionRGBSumLargerThanValue = 0;
        static constexpr double mNightStreetLightDots1DitherProbabily = 0.01;
        static constexpr double mNightStreetLightDots2DitherProbabily = 0.02;
        static constexpr double mNightStreetLightDots3DitherProbabily = 0.05;
        static const int mNightStreetLightDot1Red = UCHAR_MAX;
        static const int mNightStreetLightDot1Green = UCHAR_MAX;
        static const int mNightStreetLightDot1Blue = UCHAR_MAX;
        static const int mNightStreetLightDot2Red = UCHAR_MAX;
        static const int mNightStreetLightDot2Green = 200;
        static const int mNightStreetLightDot2Blue = 140;
        static const int mNightStreetLightDot3Red = UCHAR_MAX;
        static const int mNightStreetLightDot3Green = 180;
        static const int mNightStreetLightDot3Blue = 80;
        static const int mNightStreetRedAddition = 100;
        static const int mNightStreetGreenAddition = 50;
        static const int mNightStreetBlueAddition = -50;
        static constexpr float mNightNonStreetLightness = 0.5;
        static const bool mSpareOutWaterForSeasonsGeneration = false;
        static const bool mNoSnowInWaterForWinterAndHardWinter = false;
        static const bool mHardWinterStreetsConditionOn = true;
};

void foreach_pixel(Image *img, void (*callback)(Quantum *));
bool pixelIsWaterOrWaterTransition(Quantum *pixel);
void c_create_night(string imgName, string outName);
void c_create_hard_winter(string imgName, string outName);
void c_create_autumn(string imgName, string outName);
void c_create_spring(string imgName, string outName);
void c_create_winter(string imgName, string outName);

#endif

