#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python S

# Run migrations
flask db upgrade
