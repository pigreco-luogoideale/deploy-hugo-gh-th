from starlette.applications import Starlette
from starlette.responses import JSONResponse
import uvicorn
import configparser

VERSION = "0.0.1"

config = configparser.ConfigParser()
config.read('deploy.conf')
print(list(config.keys()))

app = Starlette(debug=True)

@app.route('/', methods=["POST"])
async def homepage(request):
    data = await request.json()  # Github sends the payload as JSON

    # Check repository we have to update
    repo = data.get("repository", {}).get("full_name")
    if repo is None:
        return JSONResponse({"status": 400, "message": "Unable to retrieve repository full name"})

    if repo not in config:
        return JSONResponse({"status": 400, "message": f"Unable to find repository {repo}"})

    # TODO clone, compile, push to FTP

    return JSONResponse({"status": 200, "message": f"Repo {repo} found"})


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
