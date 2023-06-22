from pymongo import MongoClient
from typing import Final
import os

database: Final = MongoClient(os.environ["ATLAS_URI"]).get_database("coc_events")