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

sed -i -e 's/\r$//' /vagrant/Ortho4XP_starter.sh /vagrant/Ortho4XP_provision_script.sh /vagrant/Ortho4XP_vboxguestadditions.sh

chmod a+x /vagrant/Ortho4XP_starter.sh
chmod a+x /vagrant/Ortho4XP_vboxguestadditions.sh

Ortho4XP_App=/vagrant/Ortho4XP_App.desktop
Ortho4XP_VB_Fix=/vagrant/Ortho4XP_fixvbguest.desktop

chmod a+x $Ortho4XP_App
chmod a+x $Ortho4XP_VB_Fix

starter=/usr/local/bin/Ortho4XP_starter
local_app_dir=/home/vagrant/.local/share/applications
desktop_dir=/home/vagrant/Desktop

Ortho4XP_App_local="$local_app_dir/Ortho4XP_App.desktop"
Ortho4XP_fixvbguest_local="$local_app_dir/Ortho4XP_fixvbguest.desktop"

Ortho4XP_App_Desktop="$desktop_dir/Ortho4XP.desktop"
Ortho4XP_fixvbguest_Desktop="$desktop_dir/Fix_VB.desktop"

if [ ! -L $starter ]; then
  ln -s /vagrant/Ortho4XP_starter.sh $starter
fi

if [ ! -L $local_app_dir ]; then
  mkdir -p $local_app_dir
  mkdir -p $desktop_dir
fi

if [ ! -L $Ortho4XP_App_local ]; then
  cp $Ortho4XP_App $Ortho4XP_App_local

  if [ ! -L $Ortho4XP_App_Desktop ]; then
    ln -s $Ortho4XP_App_local $Ortho4XP_App_Desktop
  fi
fi

if [ ! -L $Ortho4XP_fixvbguest_local ]; then
  cp $Ortho4XP_VB_Fix $Ortho4XP_fixvbguest_local

  if [ ! -L $Ortho4XP_fixvbguest_Desktop ]; then
    ln -s $Ortho4XP_fixvbguest_local $Ortho4XP_fixvbguest_Desktop
  fi
fi
