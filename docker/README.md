# Ortho4XP in a container

## Build the container (once)

```sh
docker build -f Dockerfile -t ortho4xp ..
```

# Run the container (for each tile you need)

```sh
docker run --rm -it -v $PWD/out/Tiles:/Ortho4XP/Tiles ortho4xp 45 -074 Arc 17
```

The `-v $PWD/out/Tiles:/Ortho4XP/Tiles` switch tells docker to mount the `Tiles` output folder into the current working directory.  

The last four parameters are:

- the coordinate of the tile (`45 -074` include Montréal, QC, Canada, with the CYUL airport)
- the map provider (`Arc`)
- and the zoom level (`17`) 
