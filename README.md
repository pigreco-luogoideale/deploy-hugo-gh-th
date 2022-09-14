# Development

Setup virtual environment:

    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip3 install -r requirements.txt

Run the uvicorn server:

    $ python3 server.py

# Deploy

Use nix to build and podman (or docker, if you have to) to deploy the image:

    $ podman load < $(nix build .#server_image)
    $ podman run -it --rm -p 33099:8000 \
                 -v "$PWD/config/:/.config/:Z" \
                 -v "$PWD/repos:/autopub/repos:Z" \
                 -v "$PWD/deploy.conf:/autopub/deploy.conf:Z" \
                 localhost/deploy_app

While the image for GHA is built using `nix build .#gha_image` and uploaded to
docker.io/akiross/zola-build-and-rclone

Note that I am using Z flag here to ensure reading permissions. A few things
are expected to be in place when running:
 - `/.config/rclone/rclone.conf`
 - `/autopub/deploy.conf` is the deploy configuration
 - `/autopub/repos` is where repos are cached, it might be convenient to mount

## Configuration

You will probably need to create a configuration file first. For that, create
the `config` directory and run the docker with the command `rclone config`,
then follow the procedure for your FTP.
Run that command every time you need to support another FTP server.

In the `deploy.conf` file you have to configure the websites that you want to
deploy. The purposes are multiple:

 1. ensure your are deploying only authorized repositories
 2. provide rclone deploy target, e.g. `luogoideale:/htdocs/`
 3. (optionally) provide hugo source folder (default is `public`)

An example configuration is the following:

    [pigreco-luogoideale/hugo-site]
    rclone_target = luogoideale:/htdocs/
    secret = expected_github_secret

In this case, `rclone_target` is the name and directory where rclone will copy
the content of the `public` directory, created by hugo. The target name,
`luogoideale`, is the one chosen during `rclone config`.

The (currently unused) field `secret` is checked against the github secret
provided in webhook configuration, providing a basic check that the deploy is
authorized.
