from starlette.applications import Starlette
from starlette.responses import JSONResponse
import uvicorn
import configparser

config = configparser.ConfigParser()
config.read('deploy.conf')

app = Starlette(debug=True)

@app.route('/')
async def homepage(request):
    data = await request.json()  # Github sends the payload as JSON

    # Check repository we have to update
    repo = data["repository"]["full_name"]

    return JSONResponse(dict(config))


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
