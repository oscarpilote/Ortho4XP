#!/usr/bin/env bash
set -e

ten_floor () {
  python3 -c "import math; print ('{:+0$2d}'.format(int(math.floor((int(\"$1\", 10))/10)*10)))"
}

plus_one() {
  python3 -c "print ('{:+0$2d}'.format(int(\"$1\")+1))"
}

usgs_fn() {
  local latp1 lon
  latp1=$(plus_one $1 3 | tr '+-' 'ns')
  lon=$(echo $2 | tr '+-' 'ew')

  echo "USGS_13_${latp1}${lon}.tif"
}

usgs_dl() {
  local latp1 lon url
  latp1=$(plus_one $1 3 | tr '+-' 'ns')
  lon=$(echo $2 | tr '+-' 'ew')
  url="https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/${latp1}${lon}/$(usgs_fn $1 $2)"

  if [ ! -s "/build/Geotiffs/$(usgs_fn $1 $2)" ]; then
    echo Downloading USGS data for $1 $2
    wget -nv -t 5 -O "/build/Geotiffs/$(usgs_fn $1 $2)" "$url" || echo "No USGS tile for $1 $2"
  fi
}

if [ -z "$2" ] || [ ! -z "$5" ]; then
  echo "args: lat lon [provider] [zl]"
  echo "providers: BI (bing)"
  echo "GUI not supported for docker version (yet)"
  exit 1
fi

mf="$(ten_floor $1 3)$(ten_floor $2 4)"

if [ "$FORCE" != "true" ] && [ -d "/scenery/Tiles/zOrtho4XP_${1}${2}" ]; then
  echo Tile already built for $1 $2, use FORCE=true to override
  exit 1
fi

extract_hd4_mesh_tile () {
  mkdir -p "/overlay_tile/Earth nav data"
  7z x -o"/overlay_tile/Earth nav data" /overlay/XP11_HD_Mesh_V4_${mf}*.zip "${mf}/${1}${2}*"
}

[ -d /config ] || mkdir /config
cp -p /ortho4xp/Ortho4XP.cfg /config/Ortho4XP.cfg
echo "custom_overlay_src=/overlay_tile" >> /config/Ortho4XP.cfg
echo "imprint_masks_to_dds=True" >> /config/Ortho4XP.cfg
sed -i 's/cover_airports_with_highres=.*/cover_airports_with_highres=ICAO/' /config/Ortho4XP.cfg
sed -i 's/max_convert_slots=.*/max_convert_slots=8/' /config/Ortho4XP.cfg

[ -r ./Ortho4XP.cfg ] || ln -s /config/Ortho4XP.cfg ./Ortho4XP.cfg

for d in Previews OSM_data Masks Orthophotos Elevation_data Geotiffs Patches; do
  [ -d "/build/$d" ] || mkdir "/build/$d"
  [ -L "./$d" ] || ln -s "/build/$d" "./$d"
done


for d in Tiles yOrtho4XP_Overlays; do
  [ -d "/scenery/$d" ] || mkdir "/scenery/$d"
  [ -L "./$d" ] || ln -s "/scenery/$d" "./$d"
done

[ -L ./tmp ] || ln -s /tmp ./tmp


rm Ortho4XP.cfg
ln -s /config/Ortho4XP.cfg ./Ortho4XP.cfg

# figure out if overlay is HD mesh or Xplane directory
lat_major=$(ten_floor $1 3)
lon_major=$(ten_floor $2 4)

if ls /overlay/XP11_HD_Mesh_V4_${lat_major}${lon_major}*.zip 1> /dev/null 2>&1; then
  extract_hd4_mesh_tile "$1" "$2"
elif [ -d "/overlay/Global Scenery/X-Plane 11 Global Scenery/Earth nav data" ]; then
  mkdir -p /overlay_tile
  ln -s  "/overlay/Global Scenery/X-Plane 11 Global Scenery/Earth nav data" "/overlay_tile/Earth nav data"
else
  echo "Please provide a mesh mounted at /overlay"
  echo "This should be either the X-Plane directory, or a directory containing the HD Mesh V4 zipfiles"
  exit 1
fi

usgs_dl "$1" "$2"

if [ "$ENABLE_USGS" == "true" ]; then
  usgs="/build/Geotiffs/$(usgs_fn $1 $2)"
  if [ -s "$usgs" ]; then
    echo Using GSPS DEM file $usgs
    echo "custom_dem=$usgs" >> /config/Ortho4XP.cfg
  fi
fi

[ -z $3 ] && exec python3 /ortho4xp/Ortho4XP_v130.py "$@" "BI" "16" \
  || exec python3 /ortho4xp/Ortho4XP_v130.py "$@"
