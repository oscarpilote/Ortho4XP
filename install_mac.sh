#! /bin/bash
if [ ! -f "Ortho4XP.py" ]; then
    echo " "
    echo "Error!"
    echo " "
    echo "install_mac.sh must be located in the main Ortho4XP directory."
    echo " "
    exit 1 
fi

if ! [ -x "$(command -v brew)" ]; then
    echo " "
    echo "Error!"
    echo "Homebrew must be installed first: https://brew.sh"
    echo " "
    exit 1
fi

echo " "
echo "Setting up Ortho4XP...."
echo " "

# Install software dependencies from brew
brew install python python-tk spatialindex p7zip proj gdal

# Create a Python virtual environment
python3 -m venv venv

# Activate the Python virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Allow macOS to run required tools
xattr -dr com.apple.quarantine ./Utils/mac/*

# Make start_mac.sh file executable
chmod 755 start_mac.sh

echo " "
echo "Ortho4XP setup complete!"
echo "Use ./start_mac.sh to run Ortho4XP"
echo " "
