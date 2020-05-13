# Install the latest version of Python on your Mac. 
# Download and install Ortho4XP on your Mac.
# Go to the Ortho4XP folder  cd /path/to/Ortho4XP 
# THEN run this script.

# Install Homebrew Master (ruby install is depreciated)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"



# Install dependencies
brew install python gdal spatialindex p7zip

# Install pyproj
pip3 install cython
pip3 install git+https://github.com/jswhit/pyproj.git

# Install other dependencies
pip3 install numpy shapely rtree pillow requests
