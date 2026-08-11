#!/bin/bash

set -e

part=${1:-patch}

uvx bump-my-version bump "$part"
git push
git push --tags