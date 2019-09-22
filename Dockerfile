#
# First stage: download and unpack rclone
#
FROM alpine:3.10

# We need curl for downloading rclone
RUN apk add curl 
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip
RUN unzip rclone-current-linux-amd64.zip
RUN cp /rclone-*-linux-amd64/rclone /

#
# Second stage: prepare image with rclone and python
#
FROM python:3.7-alpine3.10
LABEL maintainer="github.com/pigreco-luogoideale"

# We need rclone to download the old website (backup) and upload the new data
COPY --from=0 /rclone /usr/bin

# We need gcc for building pip packages
RUN apk add --no-cache build-base

# Install all the things!
ADD . /autopub/
WORKDIR /autopub
RUN pip install -r requirements.txt

# Drop build base
RUN apk del build-base

# Run the server
CMD python3 server.py
