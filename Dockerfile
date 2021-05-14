#
# First stage: download and unpack rclone, hugo and zola
#
FROM alpine:3.10

# We need curl for downloading rclone
RUN apk add curl 
ARG RCLONE_VERSION=v1.55.0
RUN curl -s -O https://downloads.rclone.org/${RCLONE_VERSION}/rclone-${RCLONE_VERSION}-linux-amd64.zip
RUN unzip rclone-${RCLONE_VERSION}-linux-amd64.zip
RUN cp /rclone-${RCLONE_VERSION}-linux-amd64/rclone /

# Download hugo and unpack
ARG HUGO_VERSION=0.58.3
ADD https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_${HUGO_VERSION}_Linux-64bit.tar.gz /tmp
RUN tar -xf /tmp/hugo_${HUGO_VERSION}_Linux-64bit.tar.gz -C /tmp

# Download zola and unpack
ARG ZOLA_VERSION=0.13.0
ADD https://github.com/getzola/zola/releases/download/v${ZOLA_VERSION}/zola-v${ZOLA_VERSION}-x86_64-unknown-linux-gnu.tar.gz /tmp
RUN tar -xf /tmp/zola-v${ZOLA_VERSION}-x86_64-unknown-linux-gnu.tar.gz -C /tmp

#
# Second stage: prepare image with rclone and python
#
FROM python:3.7-alpine3.10
LABEL maintainer="github.com/pigreco-luogoideale"

# We need rclone to download the old website (backup) and upload the new data
COPY --from=0 /rclone /usr/bin

# Copy hugo and zola to compile the website
COPY --from=0 /tmp/hugo /usr/bin
COPY --from=0 /tmp/zola /usr/bin

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
