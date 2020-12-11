Install conjure (in conjure git checkout):

make solvers && make install

Install an up-to-date savilerow (in an up to date savilerow git checkout)

./compile.sh
cp savilerow savilerow.jar ~/.local/bin


To run demystify:

pip3 install python-sat z3-solver numpy

Then try:

python3 demystify --eprime eprime/binairo.eprime --eprimeparam eprime/binairo-1.param