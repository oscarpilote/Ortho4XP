# Install Python if not found
if command -v python3 &>/dev/null; then
    echo "python3 already available"
else
    brew install python
fi

# Install dependencies
brew install gdal spatialindex p7zip proj python-tk

# Install pyproj
pip3 install pyproj

# Install other dependencies
pip3 install numpy shapely rtree pillow requests
