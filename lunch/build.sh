#!/usr/bin/env bash
set -o errexit

pip install -r lunch/requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate