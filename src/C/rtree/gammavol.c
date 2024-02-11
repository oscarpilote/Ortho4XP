#include <stdio.h>
#include <math.h>

#ifndef M_PI
#	define M_PI 3.1415926535
#endif
#ifndef ABS
#	define ABS(a) ((a) > 0 ? (a) : -(a))
#endif

#define EP .0000000001

const double log_pi = log(M_PI);

double sphere_volume(double dimension)
{
	double log_gamma, log_volume;
	log_gamma = gamma(dimension/2.0 + 1);
	log_volume = dimension/2.0 * log_pi - log_gamma;
	return exp(log_volume);
}


int main()
{
	double dim=0, delta=1;
	while(ABS(delta) > EP)
		if(sphere_volume(dim + delta) > sphere_volume(dim))
			dim += delta;
		else
			delta /= -2;
	printf("max volume = %.10f at dimension %.10f\n",
		sphere_volume(dim), dim);
	return 0;
}
