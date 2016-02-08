#!/bin/bash

rm -f ../data/data.yaml
python manage.py dumpdata --settings=settings.settings --exclude=contenttypes --exclude=admin --exclude=auth.permission --exclude=sessions.session --indent 2 --format yaml > ../data/data.yaml