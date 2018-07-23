#!/usr/bin/env bash

apt-get -y update

# This is just to make sure you have the latest Ubuntu Xenial
apt-get -y upgrade

apt-get install -y python3 \
    python3-pip \
    python3-requests \
    python3-numpy \
    python3-pyproj \
    python3-gdal \
    python3-shapely \
    python3-rtree \
    python3-pil \
    python3-pil.imagetk \
    p7zip-full

# Comment this line below if you want to have headless Ubuntu
apt-get install -y ubuntu-desktop

apt-get -y update

chmod a+x /vagrant/Ortho4XP_starter.sh
chmod a+x /vagrant/Ortho4XP_vboxguestadditions.sh

Ortho4XP_App=/vagrant/Ortho4XP_App.desktop
Ortho4XP_VB_Fix=/vagrant/Ortho4XP_fixvbguest.desktop

chmod a+x $Ortho4XP_App
chmod a+x $Ortho4XP_VB_Fix

starter=/usr/local/bin/Ortho4XP_starter
local_app_dir=/home/vagrant/.local/share/applications
Ortho4XP_App_local="$local_app_dir/Ortho4XP_App.desktop"
Ortho4XP_fixvbguest="$local_app_dir/Ortho4XP_fixvbguest.desktop"

Ortho4XP_App_Desktop=/home/vagrant/Desktop/Ortho4XP.desktop
Ortho4XP_fixvbguest_Desktop=/home/vagrant/Desktop/Fix_VB.desktop

if [ ! -L $starter ]; then
  ln -s /vagrant/Ortho4XP_starter.sh $starter
fi

if [ ! -L $local_app_dir ]; then
  mkdir -p $local_app_dir
fi

if [ ! -L $Ortho4XP_App_local ]; then
  cp /vagrant/Ortho4XP_App.desktop $Ortho4XP_App_local

  if [ ! -L $Ortho4XP_App_Desktop ]; then
    ln -s $Ortho4XP_App_local $Ortho4XP_App_Desktop
  fi
fi

if [ ! -L $Ortho4XP_fixvbguest ]; then
  cp /vagrant/Ortho4XP_fixvbguest.desktop $Ortho4XP_fixvbguest

  if [ ! -L $Ortho4XP_fixvbguest_Desktop ]; then
    ln -s $Ortho4XP_fixvbguest $Ortho4XP_fixvbguest_Desktop
  fi
fi
