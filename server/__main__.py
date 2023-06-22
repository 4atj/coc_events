from dotenv import load_dotenv
load_dotenv(".env")

from sanic import Sanic

from .user import user_routes
from .exceptions import exceptions_bluteprint

import os

app = Sanic("coc_events")

app.static('/', './client/index.html')
app.static('/', './client/')

app.blueprint(user_routes)
app.blueprint(exceptions_bluteprint)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)