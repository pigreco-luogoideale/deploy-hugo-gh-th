#!/usr/bin/env python3

import configparser
import hashlib
import hmac
import json
import logging
import os
import subprocess
import tempfile
import toml
import uvicorn

from pathlib import Path
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse
from weasyprint import HTML


config = configparser.ConfigParser()
config.read("deploy.conf")
print(list(config.keys()))

# Ensure we have a dir for repos
repos_dir = Path("repos")
repos_dir.mkdir(exist_ok=True, parents=True)
print("cwd:", Path.cwd(), "repos_dir:", repos_dir)

# Application
app = Starlette(debug=True)

# Read tokens to send status via chat
TK = os.environ.get("TG_TOKEN")
CH = os.environ.get("TG_CHAT")
HN = os.environ.get("TG_HOST")
WU = os.environ.get("SLACK_WEBHOOK_URL")


def remote_message(data, status_code=200):
    if TK and CH and HN:
        message = data.get("message")
        # Run in background, if it doesn't work it's not really a problem
        try:
            subprocess.Popen([
                "curl", "-s", "-X", "POST", "-H", "Content-Type: application/json", "-d",
                json.dumps({'chat_id': CH, 'text': f"{HN}: {message}"}),
                f"https://api.telegram.org/bot{TK}/sendMessage"
            ])
        except OSError:
            logging.warn("Cannot send remote message to telegram via curl")
    if WU:
        message = data.get("message")
        # Run in background, if it doesn't work it's not really a problem
        try:
            subprocess.Popen([
                "curl", "-s", "-X", "POST", "-H", "Content-type: application/json", "--data",
                json.dumps({'text': message}), WU,
            ])
        except OSError:
            logging.warn("Cannot send remote message to slack via curl")

    return JSONResponse(data)


@app.route("/", methods=["POST"])
async def homepage(request):
    logging.info("Received push webhook, processing")
    try:
        data = await request.json()  # Github sends the payload as JSON
    except:
        logging.info("Request has no json data associated")
        return remote_message(
            {"message": "Request is missing data"}, status_code=400
        )
    logging.info("Got data, getting repository")

    # Check repository we have to update
    repo = data.get("repository", {}).get("full_name")
    if repo is None:
        logging.error("Unable to retrieve repository full name")
        return remote_message(
            {"message": "Unable to retrieve repository full name"}, status_code=400
        )
    logging.info("Got repository")

    if repo not in config:
        logging.error(f"Unable to find repo {repo}")
        return remote_message(
            {"message": f"Unable to find repository {repo}"}, status_code=400
        )

    # Ensure payload is authorized
    secret = config[repo].get("secret")
    if secret is not None:
        # Signature of the body sent by github
        x_hub_signature = request.headers["X-Hub-Signature"]
        body = await request.body()
        signature = (
            "sha1=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        )
        if not hmac.compare_digest(signature, x_hub_signature):
            logging.error("Signature mismatch, not authorized")
            print("Got", x_hub_signature, "expected", signature)
            return remote_message({"message": "Not authorized"}, status_code=400)

    logging.info("Starting background task")

    task = BackgroundTask(build_and_upload_website, data=data, repo=repo)
    remote_message({"message": "All checks ok, background build starting..."})

    return JSONResponse(
        {"message": f"Deployment of {repo} started successfully!"},
        background=task
    )


async def build_and_upload_website(data, repo):
    """Given a repo to build, this checks it out, builds and publish it online."""
    logging.info("Building and uploading website")
    remote_message({"message": "Background build started!"})

    # Get source and target directories for rclone
    rclone_source = config[repo].get("rclone_source", "public/")
    rclone_target = config[repo].get("rclone_target")
    if rclone_target is None:
        logging.error(f"Missing rclone target in config for {repo}")
        return remote_message(
            {"message": f"Missing rclone target in config for {repo}"}, status_code=400
        )

    # Handle branches
    git_ref = data.get("ref").split("/")
    branch_name = '/'.join(git_ref[2:])  # This includes / that are legal in branch names
    logging.info(f"Obtained git ref {git_ref} and branch name {branch_name}")
    default_branch = data.get("repository", {}).get("default_branch")
    logging.info(f"Default branch is {default_branch}")

    if branch_name != default_branch:
        logging.info("Push on a non-default branch")

        if config[repo].get("publish_branches", False):
            # Non-default branches can be published, determine the subdir for publication
            logging.info("Non-default branches can be published in subdir")

            # Override rclone target using the one for branches. Fail if unset
            rclone_target = config[repo].get("rclone_target_branches")
            if rclone_target is None:
                logging.error(f"Missing rclone target for branches in config for {repo}")
                return remote_message(
                    {"message": f"Missing rclone target for branches in config for {repo}"}, status_code=400
                )
            # Replace {branch} with branch name
            rclone_target = rclone_target.replace("{branch}", branch_name)
        else:
            return remote_message(
                {"message": "Publishing branches not enabled"}, status_code=400
            )

    # Retrieve the URL of the repo to clone
    clone_url = data.get("repository", {}).get("clone_url")
    if clone_url is None:
        logging.error("No clone_repository key found")
        return remote_message(
            {"message": "No clone_repository key found"}, status_code=400
        )

    # Clone or fetch the repo, depending if exists or not
    # repo should contain author and repo (e.g. pigreco-luogoideale/hugo-site)
    # so the repo is organized by author and we should not have clashes
    if (repos_dir / repo).is_dir():
        logging.info(f"Fetching repository {repo}")
        status = subprocess.run(["git", "fetch", "--all"], cwd=(repos_dir / repo))
    else:
        logging.info(f"Cloning repository {clone_url} into {repo}")
        status = subprocess.run(["git", "clone", clone_url, repo], cwd=repos_dir)

    if status.returncode != 0:
        logging.error("Unable to fetch repo")
        return remote_message({"message": "Unable to fetch repo"}, status_code=400)

    # Checkout correct branch
    status = subprocess.run(["git", "checkout", branch_name], cwd=(repos_dir / repo))
    if status.returncode != 0:
        logging.error("Unable to checkout branch %s", branch_name)
        return remote_message({"message": f"Unable to checkout branch {branch_name}"}, status_code=400)

    # Pull the changes
    status = subprocess.run(["git", "pull"], cwd=(repos_dir / repo))
    if status.returncode != 0:
        logging.error("Unable to pull branch %s", branch_name)
        return remote_message({"message": f"Unable to pull branch {branch_name}"}, status_code=400)

    # Determine if this is a zola or hugo website
    with (repos_dir / repo / "config.toml").open() as inf:
        site_conf = toml.load(inf)
        # Zola uses base_url while hugo uses baseURL
        is_zola = 'base_url' in site_conf

        # Check if weasyprint is expected to run
        pdf_targets = site_conf.get('extra', {}).get('weasyprint', {})
        # return remote_message({"message": f"Repo {repo} successfully deployed!"})
        if pdf_targets:
            logging.info("Website has pdf targets, building")
            # start zola serve
            child = subprocess.Popen(
                ["zola", "serve"],
                cwd=(repos_dir / repo),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            # Wait for 127.0.0.1:1111 to be printed, so we know server is up
            for line in child.stdout:
                if b'127.0.0.1:1111' in line:
                    logging.info("zola server up and running!")
                    break

            try:
                # Build pdfs for each target
                for name, info in pdf_targets.items():
                    url = info.get("url")
                    out = info.get("out")
                    if not url or not out:
                        return remote_message(
                            {"message": f"PDF target {name} is missing url or out in config"},
                            status_code=400,
                        )
                    pdf_path = f"{repos_dir}/{repo}/{out}"
                    logging.info(f"Weasyprinting {name} from {url} in {pdf_path}")
                    HTML(url).write_pdf(pdf_path)
                    # Ensure the file exists
                    if not Path(pdf_path).is_file():
                        return remote_message(
                            {"message": f"Unable to print {pdf_path} for PDF target {name}"},
                            status_code=400,
                        )
            except Exception as ex:
                return remote_message(
                    {"message": f"Exception occurred while printing PDF\n{ex}"},
                    status_code=400,
                )
            finally:
                # Done, let's kill the server
                child.terminate()
                child.wait()

    if is_zola:
        build_cmd = ["zola", "build"]
    else:
        build_cmd = ["hugo", "--cleanDestinationDir"]
    logging.info(f"Building site using {build_cmd[0]}")
    # We now have the repo, go there and build, cleaning destination
    status = subprocess.run(
        build_cmd,
        cwd=(repos_dir / repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if status.returncode != 0:
        logging.error(f"Unable to compile {build_cmd[0]} site")
        log = status.stdout.decode()
        for line in log.splitlines():
            logging.error(line)
        return remote_message(
            {"message": f"Unable to compile {build_cmd[0]} site", "log": log},
            status_code=400,
        )

    # Great, the site was compiled! Now upload it to ftp
    logging.info(f"Site built, uploading {rclone_source} {rclone_target}")
    status = subprocess.run(
        ["rclone", "sync", "-v", rclone_source, rclone_target],
        cwd=(repos_dir / repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if status.returncode != 0:
        logging.error("Unable to upload to FTP")
        log = status.stdout.decode()
        for line in log.splitlines():
            logging.error(line)
        return remote_message(
            {"message": "Unable to upload to FTP", "log": log},
            status_code=400,
        )

    logging.info(f"Repo {repo} successfully deployed in {rclone_target}")
    return remote_message(
        {"message": f"Repo {repo} successfully deployed in {rclone_target}"},
        status_code=200,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    remote_message({"message": "Build and deploy service started"})
    uvicorn.run(app, host="0.0.0.0", port=8000)
