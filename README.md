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
                 -v "$PWD/config:/root/.config/:Z" \
                 deploy-hugo-gh-th

Note that I am using Z flag here to ensure reading permissions.

You will probably need to create a configuration file first. For that, create
the `config` directory and run the docker with the command `rclone config`,
then follow the procedure for your FTP.
Run that command every time you need to support another FTP server.

## Configuration

TODO

# Important notes

 - The current code assumes that public is the output directory of the
   hugo website. Please, make sure your hugo project compiles correctly and
   outputs in that directory.
