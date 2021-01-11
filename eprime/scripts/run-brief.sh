python3 ../demystify --eprime $1 --eprimeparam $2 --cores 4 --incomplete --repeats 20 --steps 10 > $2.out.html 2> $2.err
python3 ../demystify --eprime $1 --eprimeparam $2 --cores 4 --incomplete --repeats 20 --steps 10 --nodomains > $2.nodomains.html 2> $2.nodomains.err
