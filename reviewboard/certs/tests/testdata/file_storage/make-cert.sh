#!/bin/sh
# Utility for constructing certificates for testing.
#
# Version Added:
#     6.0

NAME=$1
PORT=$2

openssl req \
    -newkey rsa:2048 -new -nodes -x509 -days 99999 \
    -subj "/C=US/ST=California/L=SomeTown/O=ExampleCorp/CN=${NAME}" \
    -keyout "${NAME}_${PORT}.key" \
    -out "${NAME}_${PORT}.crt"
