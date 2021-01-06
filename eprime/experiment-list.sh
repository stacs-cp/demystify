#!/usr/bin/env bash

shopt -s globstar

$* binairo.eprime binairo/**/*.param

$* nfutoshiki.eprime futoshiki/**/*.param

$* garam.eprime garam/**/*.param

$* kakuro.eprime kakuro/**/*.param

$* nice_killer.eprime killersudoku/**/*.param

$* skyscrapers.eprime skyscrapers/**/*.param

$* solitairebattleship/solitaire_battleship.eprime solitairebattleship/**/*.param

$* star-battle.eprime star-battle*.param

$* tents.eprime tents/**/*.param