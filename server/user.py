from __future__ import annotations
from typing import Final, Any

from sanic import Blueprint, Request
from sanic import HTTPResponse, json
from sanic.exceptions import BadRequest, Unauthorized
from server.database import database

from bson.objectid import ObjectId

from .clashmanager import ClashManager
from .exceptions import CocEventsException

from . import utils
import time


# Routing

user_routes: Final = Blueprint('user', url_prefix='/services/')

@user_routes.post('/login_request')
async def login_request_route(request: Request) -> HTTPResponse:
    username = str(request.json.get("username", ""))

    if not username:
        raise BadRequest("No Username was provided")
    
    session_id = utils.safe_random_string()

    login_request = LoginRequest(username)
    LoginRequest.add(session_id, login_request)

    response = json({"auth_code": login_request.auth_code})
    response.cookies["session_id"] = session_id

    return response

@user_routes.post('/login')
async def login_route(request: Request) -> HTTPResponse:
    session_id = str(request.cookies.get("session_id", ""))

    if not session_id:
        raise BadRequest("No session_id was provided")
    
    login_request = LoginRequest.get(session_id)

    if login_request is None:
        raise BadRequest(
            "There is no login request related to this session.")
    
    clash_manager = ClashManager.get()

    user = await clash_manager.search_user(login_request.username)
    user_info = await clash_manager.get_user_info(user["id"])

    if login_request.auth_code in user_info["codingamer"].get("biography", ""):
        login_request.delete(session_id)

        user = User.from_cg_document(user_info["codingamer"])
        user.session_ids.append(session_id)
        user.update_db()

        return HTTPResponse()

    raise BadRequest("Authentication failed")
    
@user_routes.post('/logout')
async def logout_route(request: Request) -> HTTPResponse:
    user = authenticate(request)
    session_id = str(request.cookies.get("session_id", ""))
    user.session_ids.remove(session_id)
    user.update_db()

    response = HTTPResponse()
    response.cookies["session_id"] = ""

    return response

@user_routes.post("/authenticate")
def authenticate_route(request: Request) -> HTTPResponse:
    return json(authenticate(request).all_info())

def authenticate(request: Request) -> User:
    if "session_id" not in request.cookies:
        raise BadRequest("session_id was not provided")
    
    try:
        return User.get_by_session_id(request.cookies["session_id"])
    
    except UserException as exception:
        raise Unauthorized(exception.msg)


# User

user_collection: Final = database.get_collection("users")

class LoginRequest:
    timeout_delay: Final[float] = 300 # secs
    login_requests: Final[dict[str, LoginRequest]] = {}

    def __init__(self, username: str) -> None:
        self.creation_time = time.time()
        self.auth_code = utils.safe_random_string()
        self.username = username

    @classmethod
    def add(cls, session_id: str, login_request: LoginRequest):
        cls.login_requests[session_id] = login_request
        cls.delete_timedout_requests()

    @classmethod
    def get(cls, session_id: str, __default: LoginRequest | None = None) -> LoginRequest | None:
        cls.delete_timedout_requests()
        return cls.login_requests.get(session_id, __default)
    
    @classmethod
    def delete(cls, session_id: str):
        del cls.login_requests[session_id]

    @classmethod
    def delete_timedout_requests(cls):
        for session_id, login_request in cls.login_requests.copy().items():
            if not login_request.is_timed_out():
                break
            cls.delete(session_id)
            
    def is_timed_out(self) -> bool:
        return self.creation_time + LoginRequest.timeout_delay < time.time()

class UserException(CocEventsException):
    pass

class User:
    def __init__(self, user_id: str, username: str, public_handle: str, avatar_id: str, session_ids: list[str], is_admin: bool) -> None:
        self.user_id = user_id
        self.username = username
        self.public_handle = public_handle
        self.avatar_id = avatar_id
        self.session_ids = session_ids
        self.is_admin = is_admin
    
    def insert_into_db(self):
        user_collection.insert_one({
            "_id": ObjectId(self.user_id.zfill(24)),
            "username": self.username,
            "public_handle": self.public_handle,
            "avatar_id": self.avatar_id,
            "session_ids": self.session_ids,
            "is_admin": self.is_admin
        })

    def update_db(self) -> None:
        filter = {"_id": ObjectId(self.user_id.zfill(24))}
        document = {
            "$set": {
                "_id": ObjectId(self.user_id.zfill(24)),
                "username": self.username,
                "public_handle": self.public_handle,
                "avatar_id": self.avatar_id,
                "session_ids": self.session_ids,
                "is_admin": self.is_admin
            }
        }
        user_collection.update_one(filter, document, upsert = True)
    
    def public_info(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "public_handle": self.public_handle,
            "avatar_id": self.avatar_id,
            "session_ids": self.session_ids
        }
    
    def all_info(self) -> dict[str, Any]:
        return {
            **self.public_info(),
            "is_admin": self.is_admin
        }

    @classmethod
    def from_db_document(cls, document: dict[str, Any]):
        return cls(
            user_id = str(document["_id"]).rstrip("0"),
            username = document["username"],
            public_handle = document["public_handle"],
            avatar_id = document["avatar_id"],
            session_ids = document["session_ids"],
            is_admin = document["is_admin"]
        )
    
    @classmethod
    def from_cg_document(cls, document: dict[str, Any]):
        try:
            user = cls.get_by_user_id(str(document["userId"]))

        except UserException:
            user = User(
                user_id = str(document["userId"]),
                username = "",
                public_handle = "",
                avatar_id = "",
                session_ids = [],
                is_admin = False
            )

        user.username = document["pseudo"]
        user.public_handle = document["publicHandle"]
        user.avatar_id = document.get("avatar", "")

        return user
    
    @classmethod
    def get_by_user_id(cls, user_id: str) -> User:
        user_document = user_collection.find_one({'_id': user_id})

        if user_document is None:
            raise UserException("Can't find user")
        
        return cls.from_db_document(user_document)

    @classmethod
    def get_by_session_id(cls, session_id: str) -> User:
        user_document = user_collection.find_one({'session_ids': {'$in': [session_id]}})

        if user_document is None:
            raise UserException("Session is not logged in to any user account")
        
        return cls.from_db_document(user_document)
