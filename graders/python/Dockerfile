FROM amazonlinux:2

# Needed to properly handle UTF-8
ENV PYTHONIOENCODING=UTF-8
ENV LANG=en_US.UTF-8

COPY install.sh requirements.txt /
COPY python_autograder /python_autograder

RUN /bin/bash /install.sh
