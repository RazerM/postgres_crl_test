#!/usr/bin/env python3
from os import chdir
import delegator as d

_root_pass = 'root-ca-password'
_intermediate_pass = 'intermediate-ca-password'

VERSION = '9.6'
PORT = {'9.4': 5432, '9.5': 5433, '9.6': 5434}[VERSION]


def root_passphrase(c):
    c.expect(r'(Verifying - )?Enter pass phrase for (/root/ca/)?private/ca.key.pem:')
    c.send(_root_pass)


def intermediate_passphrase(c):
    c.expect(r'(Verifying - )?Enter pass phrase for '
             r'(/root/ca/)?intermediate/private/intermediate.key.pem:')
    c.send(_intermediate_pass)


def certificate(c, common_name):
    c.expect(r'Country Name \(2 letter code\) \[.*\]:')
    c.send('DE')
    c.expect(r'State or Province Name \[.*\]:')
    c.send('Hessen')
    c.expect(r'Locality Name \[.*\]:')
    c.send('Darmstadt')
    c.expect(r'Organization Name \[.*\]:')
    c.send('Wayne Enterprises')
    c.expect(r'Organizational Unit Name \[.*\]:')
    c.send('')
    c.expect(r'Common Name \[.*\]:')
    c.send(common_name)
    c.expect(r'Email Address \[.*\]:')
    c.send('')


def sign_certificate(c):
    c.expect(r'Sign the certificate\? \[y/n\]:')
    c.send('y')
    c.expect(r'\d+ out of \d+ certificate requests certified, commit\? \[y/n\]')
    c.send('y')


def make_certificate(name, extension):
    d.run('''
        openssl genrsa \
              -out intermediate/private/{}.key.pem 2048
    '''.format(name))
    d.run('chmod 400 intermediate/private/{}.key.pem'.format(name))

    c = d.run('''
        openssl req -config intermediate/openssl.cnf \
              -key intermediate/private/{0}.key.pem \
              -new -sha256 -out intermediate/csr/{0}.csr.pem
    '''.format(name), block=False)
    certificate(c, name)
    c.block()

    c = d.run('''
        openssl ca -config intermediate/openssl.cnf \
              -extensions {1} -days 375 -notext -md sha256 \
              -in intermediate/csr/{0}.csr.pem \
              -out intermediate/certs/{0}.cert.pem
    '''.format(name, extension), block=False)
    intermediate_passphrase(c)
    sign_certificate(c)
    c.block()
    d.run('chmod 444 intermediate/certs/{}.cert.pem'.format(name))
    c = d.run('''
        openssl x509 -noout -text \
              -in intermediate/certs/{}.cert.pem
    '''.format(name))
    print(c.out)
    c = d.run('''
        openssl verify -CAfile intermediate/certs/ca-chain.cert.pem \
              intermediate/certs/{}.cert.pem
    '''.format(name))
    print(c.out)


chdir('/root/ca')

d.run('mkdir certs crl newcerts private')
d.run('chmod 700 private')
d.run('touch index.txt')
d.run('echo 1000 > serial')

c = d.run('openssl genrsa -aes256 -out private/ca.key.pem 4096', block=False)
root_passphrase(c)
root_passphrase(c)
c.block()
d.run('chmod 400 private/ca.key.pem')

c = d.run('''
    openssl req -config openssl.cnf \
          -key private/ca.key.pem \
          -new -x509 -days 7300 -sha256 -extensions v3_ca \
          -out certs/ca.cert.pem
''', block=False)
root_passphrase(c)
certificate(c, 'Some Root CA')
c.block()
d.run('chmod 444 certs/ca.cert.pem')

c = d.run('openssl x509 -noout -text -in certs/ca.cert.pem')
print(c.out)

chdir('/root/ca/intermediate')
d.run('mkdir certs crl csr newcerts private')
d.run('chmod 700 private')
d.run('touch index.txt')
d.run('echo 1000 > serial')
d.run('echo 1000 > crlnumber')

chdir('/root/ca')
c = d.run('''
    openssl genrsa -aes256 \
          -out intermediate/private/intermediate.key.pem 4096
''', block=False)
intermediate_passphrase(c)
intermediate_passphrase(c)
c.block()
d.run('chmod 400 intermediate/private/intermediate.key.pem')

c = d.run('''
    openssl req -config intermediate/openssl.cnf -new -sha256 \
          -key intermediate/private/intermediate.key.pem \
          -out intermediate/csr/intermediate.csr.pem
''', block=False)
intermediate_passphrase(c)
certificate(c, 'Some Intermediate CA')
c.block()

c = d.run('''
    openssl ca -config openssl.cnf -extensions v3_intermediate_ca \
          -days 3650 -notext -md sha256 \
          -in intermediate/csr/intermediate.csr.pem \
          -out intermediate/certs/intermediate.cert.pem
''', block=False)
root_passphrase(c)
sign_certificate(c)
c.block()
d.run('chmod 444 intermediate/certs/intermediate.cert.pem')
c = d.run('cat index.txt')
print(c.out)

c = d.run('''
    openssl x509 -noout -text \
          -in intermediate/certs/intermediate.cert.pem
''')
print(c.out)
c = d.run('''
    openssl verify -CAfile certs/ca.cert.pem \
          intermediate/certs/intermediate.cert.pem
''')
print(c.out)

d.run('''
    cat intermediate/certs/intermediate.cert.pem \
          certs/ca.cert.pem > intermediate/certs/ca-chain.cert.pem
''')
d.run('chmod 444 intermediate/certs/ca-chain.cert.pem')

c = d.run('''
    openssl ca -config intermediate/openssl.cnf \
          -gencrl -out intermediate/crl/intermediate.crl.pem
''', block=False)
intermediate_passphrase(c)
c.block()
c = d.run('openssl crl -in intermediate/crl/intermediate.crl.pem -noout -text')
print(c.out)

make_certificate('dbcluster', 'server_cert')
make_certificate('postgres', 'usr_cert')

CONFIG_DIR = '/etc/postgresql/{}/main'.format(VERSION)

# Copy these files for the server
d.run('cp /root/ca/intermediate/certs/ca-chain.cert.pem {}'.format(CONFIG_DIR))
d.run('cp /root/ca/intermediate/crl/intermediate.crl.pem {}'.format(CONFIG_DIR))
d.run('cp /root/ca/intermediate/certs/dbcluster.cert.pem {}'.format(CONFIG_DIR))
d.run('cp /root/ca/intermediate/private/dbcluster.key.pem {}'.format(CONFIG_DIR))
d.run('chown postgres:postgres {}/*.pem'.format(CONFIG_DIR))

# Copy these files for the client
d.run('cp /root/ca/intermediate/certs/ca-chain.cert.pem ~postgres')
d.run('cp /root/ca/intermediate/certs/postgres.cert.pem ~postgres')
d.run('cp /root/ca/intermediate/private/postgres.key.pem ~postgres')
d.run('chown postgres:postgres ~postgres/*.pem')

d.run('pg_ctlcluster {} main start'.format(VERSION))
c = d.run('su - postgres -c "psql -p {}"'.format(PORT), block=False)
c.send('ALTER SYSTEM SET ssl = on;')
c.send("ALTER SYSTEM SET ssl_ca_file = '{}/ca-chain.cert.pem';".format(CONFIG_DIR))
c.send("ALTER SYSTEM SET ssl_cert_file = '{}/dbcluster.cert.pem';".format(CONFIG_DIR))
c.send("ALTER SYSTEM SET ssl_key_file = '{}/dbcluster.key.pem';".format(CONFIG_DIR))

# If this line is commented, the connection with client certificate works fine.
c.send("ALTER SYSTEM SET ssl_crl_file = '{}/intermediate.crl.pem';".format(CONFIG_DIR))

c.send('\q')
c.block()

# Add hostssl/cert auth to pg_hba
d.run('''
    su - postgres -c ' \
        (tmpfile=`mktemp` && \
        {{ echo "hostssl all postgres 127.0.0.1/32 cert clientcert=1" | \
        cat - {0}/pg_hba.conf > $tmpfile && \
        mv $tmpfile {0}/pg_hba.conf; }} )'
'''.format(CONFIG_DIR))
d.run('pg_ctlcluster {} main restart'.format(VERSION))

chdir('/var/lib/postgresql')

c = d.run('''
    su - postgres -c 'psql -d " \
        sslmode=verify-ca \
        host=127.0.0.1 \
        port={} \
        sslrootcert={}/ca-chain.cert.pem \
        sslcert=postgres.cert.pem \
        sslkey=postgres.key.pem" \
        -c "SELECT 1"'
'''.format(PORT, CONFIG_DIR), block=False)
c.block()
print('Attempting client connection:')
print(c.out)

d.run('pg_ctlcluster {} main stop'.format(VERSION))
