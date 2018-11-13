#!/bin/bash

until cqlsh -u cassandra -p cassandra -f /home/cassandra/schema.cql; do
    echo "cqlsh: Cassandra is unavailable - retry later"
    sleep 2
done &

exec /docker-entrypoint.sh "$@"