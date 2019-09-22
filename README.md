# Development

Setup virtual environment:

    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip3 install -r requirements.txt

# Deploy

Use podman (or docker, if you really have to...) to build and deploy the image:

    $ podman build -t deploy-hugo-gh-th .
    $ podman run -it --rm \
                 -p 8000:8000 \
                 -v "rclone.conf:/root/.rclone.conf" \
                 deploy-hugo-gh-th

Manage the deploy as you like.
