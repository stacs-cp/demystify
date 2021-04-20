Install conjure (in conjure git checkout):

git clone https://github.com/conjure-cp/conjure && cd conjure && make && make solvers && make install

Install some python packages:

pip3 install python-sat z3-solver numpy

Then try:

python3 demystify --eprime eprime/binairo.eprime --eprimeparam eprime/binairo-1.param