# Unofficial Flykido's Ortho4XP
Ortho4XP is a scenery generator for the X-Plane flight simulator, written by _**Oscar Pilote**_

It is a really amazing tool and just like many others, I got addicted to it :)

**Please be aware that THIS IS NOT THE OFFICIAL Ortho4XP**.

This repository contains my own modifications to his tool, which I hope will one day be included in the official one.

**It may or may not work** for you, as this is all a work in progress for now.

A few resources for the original Ortho4XP :
- Forum : http://forums.x-plane.org/index.php?/forums/forum/322-ortho4xp/
- Discord Community : https://discord.gg/78nD2
- Original Ortho4XP git repository : https://github.com/oscarpilote/Ortho4XP
- Original Ortho4XP dropbox : https://www.dropbox.com/sh/cjjwu92mausoh04/AACt-QzgMRwKDL392K_Ux3cPa?dl=0

If you want to talk with me about that, I often lurk on the forum and the discord community.

I will of course add an history file to document my changes along the way : also have a look in the wiki and in the issues page.

My first intentions with this repository :
- minor code cleanup / refactoring
  - first based on pycharm buitin analyzer (pep8 checker, etc.)
  - then on external tools analysis : starting with quantifiedcode, but I'm not settled on a particular tool yet
    => see the first results here : https://www.quantifiedcode.com/app/project/gh:Flykido:Ortho4XP
  - finally, maybe I'll refactor a bit more as I see fit.
    - config files and logging : use a more standard lib for that

- add some tests along the way

- implement a few evolutions :
  - multiple layers of ZL around airports (already have a dirty patch for this, will make a cleaner one)
    => next step, even better : I know someone has implemented something to have different ZL in the corridors along the runways, I should get in touch with him
  - integration with xplane apt.dat to show them on the map
    - also use this to find the set of tiles needed along a given flight plan (or simply a given airport)
  - push the idea of simlinking from the HMI a bit further
    - also, have a "tile manager" to manage the storage location of the tiles and overlays

- maybe later, have my own go at an HMI revamp
