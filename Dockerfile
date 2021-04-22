#
# First stage: download and unpack rclone and hugo
#
FROM alpine:3.10

# We need curl for downloading rclone
RUN apk add curl 
RUN curl -s -O https://downloads.rclone.org/v1.55.0/rclone-v1.55.0-linux-amd64.zip
RUN unzip rclone-v1.55.0-linux-amd64.zip
RUN cp /rclone-*-linux-amd64/rclone /

# Download hugo as well, then unpack
ARG HUGO_VERSION=0.58.3
ADD https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_${HUGO_VERSION}_Linux-64bit.tar.gz /tmp
RUN tar -xf /tmp/hugo_${HUGO_VERSION}_Linux-64bit.tar.gz -C /tmp


#
# Second stage: prepare image with rclone and python
#
FROM python:3.7-alpine3.10
LABEL maintainer="github.com/pigreco-luogoideale"

# We need rclone to download the old website (backup) and upload the new data
COPY --from=0 /rclone /usr/bin

# Copy hugo to compile the website
COPY --from=0 /tmp/hugo /usr/bin

# We need gcc for building pip packages
# We also need git for checking out github repos
RUN apk add --no-cache build-base git

# Install all the things!
ADD . /autopub/
WORKDIR /autopub
RUN pip install -r requirements.txt

# Drop build base
RUN apk del build-base

# Run the server
CMD python3 server.py
