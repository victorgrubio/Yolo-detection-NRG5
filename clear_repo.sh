#!/bin/bash
rm -rf .git/refs/original/
rm -rf .git/logs/
git reflog expire --expire=now --all
git gc --aggressive --prune=now
git count-objects -v
