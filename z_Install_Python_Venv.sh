#! /bin/bash

path="$PWD/z_Python_Venv"

# 1. Create a Python virtual environment

python -m venv $path

# 2. Activate Python venv

source $path/bin/activate

# 3. Install packages with pip

pip install -r $PWD/requirements_nover.txt

# 4. DONE

echo " "
echo "Preparation complete!"
echo " "
echo "Use \"$path/bin/python $PWD/Ortho4XP\" to start O4XP"
echo " "
echo " "

# Function: Pause
function pause(){
   read -p "$*"
}

pause "Press enter to continue... "
