# Ortho4XP
A scenery generator for the X-Plane flight simulator

## Docker usage

### With docker-compose

Tested only with an host under Ubuntu18.04 LTS.

Allow graphical access from other clients
```
sudo apt install x11-xserver-utils
xhost local:root
```
You shoud have the response `access control disabled, clients can connect from any host`. The `xhost +` must be run after each host reboot.

In this projet directory, run
```
docker-compose build
docker-compose -u "$(id -u ${USER}):$(id -g ${USER})" up
```
The graphical interface should open.
Use the GUI to generate your tiles.

Your tiles can be found in `./Tiles`.
Your overlays can be found in `./yOrtho4XP_Overlays`.

If for whatever raison you need a shell in the container, you can use in another terminal
```
docker-compose exec ortho4xp bash
```


Bon vol !
