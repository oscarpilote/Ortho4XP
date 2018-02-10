#!/bin/bash
echo
echo "Installation of Homebrew (accept every choice with default value)"
echo "----------------------------------------------------------------------"
echo
exec ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
echo
echo "Installation of Python 3"
echo "--------------------------"
echo
exec brew install python3
echo
echo "Installation of Imagemagick"
echo "---------------------------"
echo
exec brew install imagemagick
echo
echo "Installation of python/requests"
echo "-------------------------------"
echo
exec pip3 install requests
echo
echo "Installation of python/overpy"
echo "-----------------------------"
echo
exec pip3 install overpy
echo
echo "Installation of python/numpy"
echo "-----------------------------"
echo
exec pip3 install numpy
echo
echo "Installation of python/pillow"
echo "-----------------------------"
echo
exec brew install libtiff libjpeg webp little-cms2
exec pip3 install Pillow
echo
echo "Installation of python/pyproj (optional)"
echo "----------------------------------------"
echo
exec pip3 install pyproj
echo
echo "Installation succesful (hopefully)!"


