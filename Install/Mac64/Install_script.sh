#!env bash

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
echo "Installing additional dependencies"
echo
brew install spatialindex

for dep in "numpy" "requests" "pyproj" "shapely" "rtree" ; do
    echo
    echo "Installation of python/${dep}"
    echo "--------------------------------"
    $pip_command install $dep
done

echo
echo "Installation successful (hopefully)!"

