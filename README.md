# Development

Setup virtual environment:

    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip3 install -r requirements.txt

Run the uvicorn server:

    $ python3 server.py

# Deploy

Use podman (or docker, if you really have to...) to build and deploy the image:

    $ podman build -t deploy-hugo-gh-th .
    $ podman run -it --rm \
                 -p 8000:8000 \
                 -v "rclone.conf:/root/.config/rclone/rclone.conf:Z" \
                 deploy-hugo-gh-th

Note that I am using Z flag here to ensure reading permissions.
