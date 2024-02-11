#pragma once

struct DEM {
	int epsg_code;
	double tl, tr, bl, br;
	uint32_t pixx, pixy;
	uint8_t bpp;
	uint16_t flags;
	float scale, offset;
	float *data;
	void *encoded_data;
};


