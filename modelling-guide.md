# Demystify Modelling Instructions

Demystify reads puzzle models written in Essence Prime.
The Essence Prime models are _annotated_ to let Demystify interpret the meaning of 
every variable in the model.

A normal Essence Prime comment starts with the character `$`. A Demystify annotation starts with the characters `$#`. Therefore, each Demystify annotation is an Essence Prime comment with special syntax.

All variables in the Essence Prime model should be annotated with one of `VAR`, `CON` or `AUX`:
* `VAR`: indicates a variable which would be completed by the puzzle solver
* `CON`: represents a constraint of the problem
* `AUX`: is any other variable required just to express the problem

There can also be one special description, to describe the puzzle as whole:

* `DESC`: description of the puzzle rules.

For example, given a Sudoku the set of empty cells would be annotated as `VAR`, while the _alldifferent_ constraints for each row, column and cage would be annotated as `CON`.

## `VAR` and `AUX` Annotations

`VAR` and `AUX` annotations should be positioned on top of the `find` statement in the Essence Prime file. They only take the name of the variable.

Two examples for `VAR` and `AUX` constraints follow:
```
$#VAR field
find field: matrix indexed by [RANGE, RANGE] of RANGE
```

```
$#AUX sky_left
find sky_left : matrix indexed by [int(1..4),RANGE] of RANGE
```

## `CON` Annotation

The `CON` annotation looks like

```$#CON name "English Description"```


Where the English description describes the constraint. This can include Python code inside `{}`, with the following special functions:

* `I(i)` is the ith index of the CON variable (so for `x[1,4]`, `I(1)` is `1` and `I(2)` is `4`).
* `L(i)` turns `i` into the i^th letter of the alphabet, so `L(3)` is `C`.
* `P(name [, indices])` gets the value of parameter `name`. If `name` is a matrix, then it is indexed with `indices`. All matrices are treated as 1-indexed.


## Modelling 

* Think carefully which bits of the model need to be reified. You even need to reify hard constraints, like there can only be one number in each cell, if it can *ever* be necessary for an explanation. But you can have constraints which are not open to be in MUSs: for example if N is the maximum number in a cell then you probably don't need to reify that the number in a cell is no more than N.
* You need to be careful about how much of a constraint you reify.  Sometimes you might need to reify more than you think and other times less.  For example, you might want to express an equality of a sum by saying a sum is both less= and greater=.  It might be necessary to reify around both of these together if it's not really useful to consider that as two things.  But in other cases it might be much better to reify them separately, where e.g. calculations are being done on the lower bound of some cells and explanations would be much clearer expressed this way. 
* Sometimes you want redundant constraints even where they are useless for solving. A classic example would be all diff where you might want to add all the binary inequalities between cells as well as the main all diff, since the former might lead to simpler explanations.



# Formalisms
* `Size` -> Final board size/dimensions
* `Clues`/`initial`/`values` -> Initial board with given clues
* `Grid` ->
* `Count` -> count on how many 'object' (tents/therms) there are on the whole board
* `Step` -> annotation help with objects
* `Therms`/`Trees` -> grid of thermometers
* `Rows` / `Cols` -> 
* `Board` -> matrix for the whole puzzle 
* `Cage` -> an identified shape of cells which does not necessarily havbe to be in a rectangular shape
* `TopBorder`/`BottomBorder`/`LeftBorder`/`RightBorder` -> numbers that are placed around the board in line with the rows or columns (rowsum/colsum)


## Implemented visualisations


* CellBorders: Highlight the boundaries between some cells. This is given as a matrix, where the boundary between two cells is highlighted if the cells take different values

* InnerCellBorders: A dotted inner border for a cell, implemented similarly to CellBorders.


* cornerNumbers: A number to show in the top-left square of a cell (TODO: How to specify this? - it is used in Killer Sudoku)

* rowsums, colsums: Numbers to put on the left, and top, of the grid.

* rightLabels, bottomLabels: Labels between cells

* Background: A map from integers to pictures, showing alternative images when a cell is assigned a value.

* 
