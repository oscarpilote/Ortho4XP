all: fast_image_mask

fast_image_mask: FSET_ports.o
	g++ -fpic -shared -I /usr/include/python3.5/ `Magick++-config --cxxflags --cppflags` -o fast_image_mask.so fast_image_mask.cpp	-O2 `Magick++-config --ldflags --libs` -lpython3.5m FSET_ports.o
FSET_ports.o: FSET_ports.cpp
	g++ -fpic -c `Magick++-config --cxxflags --cppflags` -O2 `Magick++-config --ldflags --libs` FSET_ports.cpp
test: fast_image_mask_test.cpp FSET_ports.o
	g++ -fpic -Wno-write-strings -o fast_image_mask_test `Magick++-config --cxxflags --cppflags` -O2 `Magick++-config --ldflags --libs` fast_image_mask_test.cpp FSET_ports.o
valgrind: test
	valgrind --leak-check=full --show-leak-kinds=all ./fast_image_mask_test
clean:
	rm -rf *.o
	rm fast_image_mask_test
