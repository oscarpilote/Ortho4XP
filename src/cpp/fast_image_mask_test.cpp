#include "FSET_ports.h"

int main(void) {
    c_create_night("TEST.bmp", "TEST_night.bmp", "TEST.tif");
    c_create_hard_winter("TEST.bmp", "TEST_hard_winter.bmp", "TEST.tif");
    c_create_autumn("TEST.bmp", "TEST_autumn.bmp", "TEST.tif");
    c_create_spring("TEST.bmp", "TEST_spring.bmp", "TEST.tif");
    c_create_winter("TEST.bmp", "TEST_winter.bmp", "TEST.tif");
    
    return 0;
}
