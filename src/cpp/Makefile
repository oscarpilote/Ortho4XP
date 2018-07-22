all: fast_image_mask

fast_image_mask:
	g++ -fpic -shared -I /usr/include/python3.5/ `Magick++-config --cxxflags --cppflags` -O2 `Magick++-config --ldflags --libs` -lpython3.5m -o fast_image_mask.so fast_image_mask.cpp

