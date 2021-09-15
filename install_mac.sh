# Install dependencies
brew install python gdal spatialindex p7zip

# Install poetry
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py| python -

# Install dependencies
poetry install

# Install gdal
poetry run pip3 install gdal
