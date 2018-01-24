#!/bin/bash

if ! which -s brew ; then
    echo
    echo "Installation of Homebrew (accept every choice with default value)"
    echo "----------------------------------------------------------------------"
    echo
    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
fi

if ! which -s python3 ; then
    echo
    echo "Installation of Python 3"
    echo "--------------------------"
    echo
    brew install python3
    pip_command=$(which pip3)
fi

# Some people may be using pyenv (or something similar), and as such, use pip instead of pip3
if [[ "$(which -s pip && pip -V | grep 'python 3')" != "" ]] ; then
    echo "Using 'pip' instead of 'pip3'"
    pip_command=$(which pip)
fi

if ! which -s magick ; then
    echo
    echo "Installation of Imagemagick"
    echo "---------------------------"
    echo
    brew install imagemagick
fi

echo
echo "Installation of python/requests"
echo "-------------------------------"
echo
$pip_command install requests

echo
echo "Installation of python/overpy"
echo "-----------------------------"
echo
$pip_command install overpy

echo
echo "Installation of python/numpy"
echo "-----------------------------"
echo
$pip_command install numpy

echo
echo "Installation of python/pillow"
echo "-----------------------------"
echo
brew install libtiff libjpeg webp little-cms2
$pip_command install Pillow

echo
echo "Installation of python/pyproj (optional)"
echo "----------------------------------------"
echo
$pip_command install pyproj

echo
echo "Installation successful (hopefully)!"


