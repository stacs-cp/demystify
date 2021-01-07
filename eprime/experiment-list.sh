#!/usr/bin/env bash

shopt -s globstar

# This is 150 problems, we skip these for now
# $* binairo.eprime binairo/instances/**/*.param

$* binairo.eprime binairo/solving_techniques/**/*.param

$* nfutoshiki.eprime futoshiki/**/*.param

$* garam.eprime garam/**/*.param

$* kakuro.eprime kakuro/**/*.param

$* nice_killer.eprime killersudoku/**/*.param

$* skyscrapers.eprime skyscrapers/**/*.param

$* solitairebattleship/solitaire_battleship.eprime solitairebattleship/**/*.param

$* star-battle.eprime star-battle*.param

$* tents.eprime tents/**/*.param
