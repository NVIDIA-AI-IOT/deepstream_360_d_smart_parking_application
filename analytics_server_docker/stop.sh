#!/bin/sh

sudo -E docker-compose down --rmi all --volumes --remove-orphans

sudo docker image prune --filter label=stage=ui-builder --force
