# Install dependencies
brew install python gdal spatialindex p7zip

# Install pyproj
pip3 install cython
pip3 install git+https://github.com/jswhit/pyproj.git

# Install other dependencies
pip3 install numpy shapely rtree pillow requests
