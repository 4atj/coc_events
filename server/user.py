from __future__ import annotations
from typing import Final, Any

from sanic import Blueprint, Request
from sanic import HTTPResponse, json
from server.database import database

from bson.objectid import ObjectId

from .clashmanager import ClashManager
from .exceptions import CocEventsException
from . import utils
import time


user_collection = database.get_collection("users")

user_routes = Blueprint('user', url_prefix='/services/')

@user_routes.post('/singup')
async def signup_route(request: Request):
    if "username" not in request.json:
        raise CocEventsException("Username was not provided")
    
    session_id = utils.safe_random_string()
    username = str(request.json["username"])
    
    signup_request = SignupRequest(username)
    SignupRequest.add(session_id, signup_request)

    response = json({"auth_code": signup_request.auth_code})
    response.cookies["session_id"] = session_id

    return response

@user_routes.post('/finish_signup')
async def finish_signup_route(request: Request):
    if "session_id" not in request.cookies:
        raise CocEventsException("session_id was not provided")

    session_id = str(request.cookies["session_id"])
    signup_request = SignupRequest.get(session_id)

    if signup_request is None:
        raise CocEventsException(
            "There is no signup request connected to this session.\n" +
            f"This might be the result of the request timing-out after {SignupRequest.timeout_delay} seconds.")
    
    clash_manager = ClashManager.get()

    users = await clash_manager.search_user(signup_request.username)

    for user in users:
        user_info = await clash_manager.get_user_info(user["id"])

        if signup_request.auth_code in user_info["codingamer"].get("biography", ""):
            signup_request.delete(session_id)

            user = User.from_cg_document(user_info["codingamer"])
            user.session_ids.append(session_id)
            user.insert_to_db()

            return HTTPResponse()

    raise CocEventsException("Authentication failed")
    

class SignupRequest:
    timeout_delay: Final[float] = 300 # secs
    signup_requests: Final[dict[str, SignupRequest]] = {}

    def __init__(self, username: str) -> None:
        self.creation_time = time.time()
        self.auth_code = utils.safe_random_string()
        self.username = username

    @classmethod
    def add(cls, session_id: str, signup_request: SignupRequest):
        cls.signup_requests[session_id] = signup_request
        cls.delete_timedout_requests()

    @classmethod
    def get(cls, session_id: str) -> SignupRequest | None:
        cls.delete_timedout_requests()
        return cls.signup_requests.get(session_id)
    
    @classmethod
    def delete(cls, session_id: str):
        del cls.signup_requests[session_id]

    @classmethod
    def delete_timedout_requests(cls):
        for session_id, signup_request in cls.signup_requests.copy().items():
            if not signup_request.is_timed_out():
                break
            cls.delete(session_id)
            
    def is_timed_out(self) -> bool:
        return self.creation_time + SignupRequest.timeout_delay < time.time()

class User:
    def __init__(self, user_id: str, username: str, public_handle: str, avatar_id: str, session_ids: list[str]) -> None:
        self.user_id = user_id
        self.username = username
        self.public_handle = public_handle
        self.avatar_id = avatar_id
        self.session_ids = session_ids
    
    def insert_to_db(self):
        user_collection.insert_one({
            "_id": ObjectId(self.user_id),
            "username": self.username,
            "public_handle": self.public_handle,
            "avatar_id": self.avatar_id,
            "session_ids": self.session_ids
        })
    
    @classmethod
    def from_db_document(cls, document: dict[str, Any]):
        return cls(
            user_id = document["_id"],
            username = document["username"],
            public_handle = document["public_handle"],
            avatar_id = document["avatar_id"],
            session_ids = document["session_ids"]
        )
    
    @classmethod
    def from_cg_document(cls, document: dict[str, Any]):
        try:
            session_ids = cls.get_by_user_id(document["userId"]).session_ids
        except CocEventsException:
            session_ids = []

        return cls(
            user_id = document["userId"],
            username = document["pseudo"],
            public_handle = document["publicHandle"],
            avatar_id = document.get("avatar", ""),
            session_ids = session_ids
        )
    
    @classmethod
    def get_by_user_id(cls, user_id: str) -> User:
        user_document = user_collection.find_one({'_id': user_id})

        if user_document is None:
            raise CocEventsException("Can't find user")
        
        return cls.from_db_document(user_document)

    @classmethod
    def get_by_session_id(cls, session_id: str) -> User:
        user_document = user_collection.find_one({'session_ids': {'$in': [session_id]}})

        if user_document is None:
            raise CocEventsException("Session is not logged in to any account")
        
        return cls.from_db_document(user_document)

    @classmethod
    def auth(cls, request: Request) -> User:
        if "session_id" not in request.cookies:
            raise CocEventsException("session_id was not provided")
        
        return cls.get_by_session_id(request.cookies["session_id"])