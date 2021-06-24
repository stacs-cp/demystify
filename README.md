# Demystify

Pen and paper puzzles like Sudoku, Futoshiki and Skyscrapers are hugely
popular. Solving such puzzles can be a trivial task for modern AI systems.
However, most AI systems solve problems using a form of backtracking, while
people try to avoid backtracking as much as possible. This means that
existing AI systems do not output explanations about their reasoning that
are meaningful to people.

Demystify is a tool which allows puzzles to be expressed in a high-level
constraint programming language and uses MUSes to automatically produce
descriptions of steps in the puzzle solving.

## Install Instructions

Install conjure (in conjure git checkout):

```
git clone https://github.com/conjure-cp/conjure && cd conjure && make && make solvers && make install
```

Install some python packages:

```
pip3 install python-sat z3-solver numpy sortedcontainers
```

Then try:

```
python3 demystify --eprime eprime/binairo.eprime --eprimeparam eprime/binairo-1.param
```

## Visualizer

Demystify also has a visual interface, which you can find in a separate repository [here](https://github.com/mmcilree/Demystify-Visualiser)

## Implemented Puzzles

* Binairo
* Futoshiki
* Sudoku
* Jigsaw Sudoku
* X-Sudoku
* [Miracle Sudoku](https://www.youtube.com/watch?v=yKf9aUIxdb4)
* Kakuro
* Skyscrapers
* Star Battle
* Tents and Trees
* Thermometers

All the models can be found in the [eprime
directory](https://github.com/stacs-cp/demystify/tree/master/eprime). If you
are interested in a puzzle that is not implemented, there is a guide for
modelling your own puzzles
[here](https://github.com/stacs-cp/demystify/blob/master/modelling-guide.md).

## Publications

* [Using Small MUSes to Explain How to Solve Pen and Paper Puzzles](https://arxiv.org/abs/2104.15040)
