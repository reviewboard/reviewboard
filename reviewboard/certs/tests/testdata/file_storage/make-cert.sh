#!/bin/sh
# Utility for constructing certificates for testing.
#
# Version Added:
#     6.0

NAME=$1
PORT=$2

NORM_NAME=`echo ${NAME} | sed s/\*/__/g`

openssl req \
    -newkey rsa:2048 -new -nodes -x509 -days 99999 \
    -subj "/C=US/ST=California/L=SomeTown/O=ExampleCorp/CN=${NAME}" \
    -keyout "${NORM_NAME}__${PORT}.key" \
    -out "${NORM_NAME}__${PORT}.crt"
