import hmac
import hashlib
import logging
import uvicorn
import subprocess
import configparser

from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import JSONResponse


VERSION = "0.2.1"

config = configparser.ConfigParser()
config.read("deploy.conf")
print(list(config.keys()))

# Ensure we have a dir for repos
repos_dir = Path("repos")
repos_dir.mkdir(exist_ok=True, parents=True)

# Application
app = Starlette(debug=True)


@app.route("/", methods=["POST"])
async def homepage(request):
    data = await request.json()  # Github sends the payload as JSON

    # Check repository we have to update
    repo = data.get("repository", {}).get("full_name")
    if repo is None:
        return JSONResponse(
            {"message": "Unable to retrieve repository full name"}, status_code=400
        )

    if repo not in config:
        return JSONResponse(
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
            return JSONResponse({"message": "Not authorized"}, status_code=400)

    rclone_source = config[repo].get("rclone_source", "public/")
    rclone_target = config[repo].get("rclone_target")
    if rclone_target is None:
        return JSONResponse(
            {"message": f"Missing rclone target in config for {repo}"}, status_code=400
        )

    # Retrieve the URL of the repo to clone
    clone_url = data.get("repository", {}).get("clone_url")
    if clone_url is None:
        return JSONResponse(
            {"message": "No clone_repository key found"}, status_code=400
        )

    # Clone or checkout the repo, depending if exists or not
    # repo should contain author and repo (e.g. pigreco-luogoideale/hugo-site)
    # so the repo is organized by author and we should not have clashes
    if (repos_dir / repo).is_dir():
        logging.info(f"Checking out repository {repo}")
        status = subprocess.run(["git", "pull"], cwd=(repos_dir / repo))
    else:
        logging.info(f"Cloning repository {clone_url} into {repo}")
        status = subprocess.run(["git", "clone", clone_url, repo], cwd=repos_dir)

    if status.returncode != 0:
        return JSONResponse({"message": f"Unable to checkout repo"}, status_code=400)

    # We now have the repo, go there and build
    status = subprocess.run(["hugo"], cwd=(repos_dir / repo))
    if status.returncode != 0:
        return JSONResponse({"message": "Unable to compile hugo site"}, status_code=400)

    # Great, the site was compiled! Now upload it to ftp
    status = subprocess.run(
        ["rclone", "copy", "-v", rclone_source, rclone_target], cwd=(repos_dir / repo)
    )
    if status.returncode != 0:
        return JSONResponse({"message": "Unable to compile hugo site"}, status_code=400)

    return JSONResponse({"message": f"Repo {repo} successfully deployed!"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
