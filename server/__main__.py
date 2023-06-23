from dotenv import load_dotenv
load_dotenv(".env")

from sanic import Sanic

from .clashmanager import ClashManager
from .user import user_routes

app = Sanic("coc_events")
app.static('/', './client/index.html')
app.static('/', './client/')
app.blueprint(user_routes)

app.config.FALLBACK_ERROR_FORMAT = "json"

if __name__ == "__main__":
    app.add_task(ClashManager.load_from_db())
    app.run(host = "0.0.0.0", port = 8080)