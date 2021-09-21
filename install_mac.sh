# Install dependencies
brew install python-tk@3.9 gdal spatialindex p7zip poetry

# Setup python environment
poetry install

# Install gdal
poetry run pip3 install gdal
