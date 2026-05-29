#!/bin/sh
# Generate a local CA + server cert/key for Postgres TLS.
# Runs in an Alpine init container; writes into a shared volume mounted at /certs.
# Idempotent — re-running with files present is a no-op.
set -eu

CERT_DIR=${CERT_DIR:-/certs}
SERVER_CN=${SERVER_CN:-postgres}
DAYS=${DAYS:-3650}
PG_UID=${PG_UID:-70}   # postgres user in postgres:*-alpine

cd "$CERT_DIR"

if [ -f server.crt ] && [ -f server.key ] && [ -f ca.crt ]; then
    echo "tls-init: certs already exist in $CERT_DIR, skipping generation"
    openssl x509 -in server.crt -noout -subject -issuer -ext subjectAltName || true
    exit 0
fi

apk add --no-cache openssl >/dev/null

echo "tls-init: generating CA"
cat > ca.cnf <<EOF
[req]
distinguished_name = req_dn
prompt = no
x509_extensions = v3_ca

[req_dn]
CN = sample-app-local-ca

[v3_ca]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
EOF

openssl req -x509 -newkey rsa:2048 -nodes \
    -config ca.cnf \
    -keyout ca.key -out ca.crt \
    -days "$DAYS"
rm -f ca.cnf

echo "tls-init: generating server cert for CN=$SERVER_CN"

# OpenSSL config with a named extensions section. Using `-extensions v3_req`
# explicitly avoids the OpenSSL 3.x case where top-level extensions in an
# extfile are silently ignored.
cat > server.cnf <<EOF
[req]
distinguished_name = req_dn
prompt = no
req_extensions = v3_req

[req_dn]
CN = $SERVER_CN

[v3_req]
subjectAltName = @alt_names
extendedKeyUsage = serverAuth
keyUsage = digitalSignature, keyEncipherment

[alt_names]
DNS.1 = $SERVER_CN
DNS.2 = localhost
IP.1  = 127.0.0.1
EOF

openssl req -new -newkey rsa:2048 -nodes \
    -config server.cnf \
    -keyout server.key -out server.csr

openssl x509 -req -in server.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days "$DAYS" \
    -extfile server.cnf -extensions v3_req

rm -f server.csr server.cnf ca.srl

# Postgres rejects the key unless it is 0600 and owned by the postgres user.
chmod 600 server.key ca.key
chown "$PG_UID:$PG_UID" server.key server.crt ca.crt

# Make CA + server cert readable to the app container too.
chmod 644 ca.crt server.crt

echo "tls-init: generated cert details:"
openssl x509 -in server.crt -noout -subject -issuer -ext subjectAltName

echo "tls-init: done"
ls -l "$CERT_DIR"
