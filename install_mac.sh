# EDIT TO GET GDAL AND ORTHO UP TO DATE WITH CURRENT Github HOMEBREW FILES


# Install dependencies
brew install  gdal spatialindex p7zip
# if only using Homebrew Python, then 
	brew install python-tk@3.9
	
#  GDAL 3.1.
# There are five major modules that are included with the GDAL Python bindings.:

# >>> from osgeo import gdal	

# Install python packages
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install cython --user
python3 -m pip install pyproj --user
python3 -m pip install numpy --user
python3 -m pip install shapely --user
python3 -m pip install rtree --user
python3 -m pip install pillow --user
python3 -m pip install requests --user
 
