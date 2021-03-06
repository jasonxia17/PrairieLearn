#!/bin/bash

yum -y update

yum install -y \
    sudo \
    gcc \
    make \
    dos2unix \
    graphviz \
    graphviz-devel

echo "setting up conda..."
cd /
curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p /usr/local -f

echo "installing Python packages..."
python3 -m pip install --no-cache-dir -r /requirements.txt

echo "Setting up autograder..."
useradd ag
chmod +x /python_autograder/run.sh
