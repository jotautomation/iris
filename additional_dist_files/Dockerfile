FROM python:3-alpine

RUN pip install wheel

RUN pip install --upgrade jot-iris

# Place you additional requirements to requirements.txt file and uncomment these lines:
# COPY requirements.txt .
# RUN pip3 install -r requirements_full.txt && deactivate


COPY . .

# Iris runs by default on port 4321
EXPOSE 4321

ENTRYPOINT ["iris.py"]


# BUILDING
#
# Note that docker will first try to find the base image (python:3-alpine) from your local computer.
# While searching it will not check the platform of the base image! Thus, if you are building
# for arm but have amd64 image locally, your image will be build for amd64. If you are building for
# same architecture always, you don't need to execute the step 1 on the instructions.
#
# Build instructions, generic for building and running in the same architecture:
# 1. docker image rm python:3-alpine
#   (Removes python:3-alpine. Remove, if you have build for some other architecture before.)
#
# 2. docker build -t [NAME_OF_THE_IMAGE:VERSION] .
#
# Cross-build instructions for arm (or any other platform)
#
# 1. docker image rm python:3-alpine
#   (Removes python:3-alpine. Remove, if you have build for some other architecture before.)
#
# 2. docker run --privileged --rm docker/binfmt:a7996909642ee92942dcd6cff44b9b95f08dad64
#    (Runs binfmt to enable qemu. See https://www.docker.com/blog/multi-platform-docker-builds/)
#
# 3. docker build --platform=arm -t [NAME_OF_THE_IMAGE:VERSION] .
#

# RUNNING
#
# docker run [NAME_OF_THE_IMAGE:VERSION]
