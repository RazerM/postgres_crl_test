FROM debian:jessie
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main" >> /etc/apt/sources.list.d/pgdg.list
RUN apt-get update && apt-get install -y wget
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
	apt-key add -
RUN apt-get update && apt-get install -y \
	postgresql-9.4 \
	postgresql-9.5 \
	postgresql-9.6 \
	openssl \
	python3 \
	python3-pexpect \
	python3-pip \
	python3-plumbum \
	vim
RUN python3 -m pip install --user delegator.py==0.0.8
RUN mkdir -p /root/ca/intermediate
COPY root-config.txt /root/ca/openssl.cnf
COPY intermediate-config.txt /root/ca/intermediate/openssl.cnf
COPY setup.py /setup.py
RUN chmod +x /setup.py && /setup.py
CMD /bin/bash