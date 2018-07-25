all: fast_image_mask

fast_image_mask: FSET_ports.o
	g++ -fpic -shared -I /usr/include/python3.5/ `Magick++-config --cxxflags --cppflags` -O2 `Magick++-config --ldflags --libs` -lpython3.5m FSET_ports.o -o fast_image_mask.so fast_image_mask.cpp

FSET_ports.o: FSET_ports.cpp
	g++ -fpic -c `Magick++-config --cxxflags --cppflags` -O2 `Magick++-config --ldflags --libs` FSET_ports.cpp

clean:
	rm -rf *.o
