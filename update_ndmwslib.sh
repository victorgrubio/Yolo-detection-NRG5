#!/usr/bin/env bash

echo -n "Importing NDMWS library... "
git submodule init
git submodule update
cp ndmws/ndmwslib/ndmws.py .
if [ -r ndmws.py ]
then
	echo "OK"
else
	echo "ERROR"
fi
