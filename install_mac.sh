# Install dependencies
# Changes current as of Big Sur
brew install  gdal spatialindex p7zip

# Install pyproj
pip3 install cython
pip3 install pyproj

# Install other dependencies
pip3 install numpy shapely rtree pillow requests

#verify your instillations with
# brew list
# pip3 list
