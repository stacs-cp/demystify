#!/usr/bin/env bash

shopt -s globstar

# This is 150 problems, we skip these for now
# $* binairo.eprime binairo/instances/**/*.param

$* skyscrapers.eprime skyscrapers/**/*.param

$* star-battle.eprime starbattle/*.param

$* tents.eprime tents/**/*.param

$* thermometer.eprime thermometer/**/*.param



$* binairo.eprime binairo/solving_techniques/**/*.param

$* nfutoshiki.eprime futoshiki/**/*.param

$* garam.eprime garam/**/*.param

$* kakuro.eprime kakuro/**/*.param


$* solitairebattleship/solitaire_battleship.eprime solitairebattleship/**/*.param

$* nice_killer.eprime killersudoku/**/*.param
