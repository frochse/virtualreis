#!/bin/bash

docker build . -t pythoncontainer
docker run -p 5000:5000 pythoncontainer:latest