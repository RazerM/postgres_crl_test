Following https://jamielinux.com/docs/openssl-certificate-authority/index.html,
this was an attempt to create root and intermediate certificates, then
configure PostgreSQL to use them.

```
$ docker build -t postgres_crl_test .
```

```
...

Attempting client connection:
psql: SSL error: tlsv1 alert unknown ca

 ---> 3aa84e2b6a6e
Removing intermediate container 4eb0b9ed3eed
Step 12/12 : CMD /bin/bash
 ---> Running in 0085b17834a7
 ---> 9e42985d37d3
Removing intermediate container 0085b17834a7
Successfully built 9e42985d37d3

```

Note that PostgreSQL did not accept the connection.

Comment out this line in `setup.py`:
```
# c.send("ALTER SYSTEM SET ssl_crl_file = '{}/intermediate.crl.pem';".format(CONFIG_DIR))
```

and now the connection works:

```
$ docker build -t postgres_crl_test .
```

```
...

Attempting client connection:
 ?column? 
----------
        1
(1 row)

 ---> 3aa84e2b6a6e
Removing intermediate container 4eb0b9ed3eed
Step 12/12 : CMD /bin/bash
 ---> Running in 0085b17834a7
 ---> 9e42985d37d3
Removing intermediate container 0085b17834a7
Successfully built 9e42985d37d3

```