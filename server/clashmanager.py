from __future__ import annotations

from time import time
import json
import asyncio
import aiohttp
from bson import ObjectId

from typing import Any, Final

from .exceptions import CocEventsException
from .database import database



class ClashError(CocEventsException):
    pass

json_headers: Final = {
    'content-type': 'application/json;charset=UTF-8',
}

clash_manager_collection: Final = database.get_collection("clash_managers")

class ClashManager:
    clash_managers: dict[str, ClashManager] = {}

    def __init__(self, id: str, token: str) -> None:
        self.id: str = id
        self.token: str = token
        self.reserved: bool = False
    
    async def initialize_session(self) -> None:
        self.session = aiohttp.ClientSession()
        self.session.cookie_jar.update_cookies({
            'rememberMe': self.token
        })
    
    def insert_into_db(self) -> None:
        clash_manager_collection.insert_one({
            "_id": ObjectId(self.id.zfill(24)),
            "token": self.token
        })

    def update_db(self) -> None:
        filter = {"_id": ObjectId(self.id.zfill(24))}
        document = {
            "$set": {
                "_id": ObjectId(self.id.zfill(24)),
                "token": self.token
            }
        }
        clash_manager_collection.update_one(filter, document, upsert = True)

    @classmethod
    async def load_from_db(cls) -> None:
        for clash_manager_document in clash_manager_collection.find():
            clash_manager = ClashManager(
                id = str(clash_manager_document['_id']).rstrip("0"),
                token = clash_manager_document['token'])
            await clash_manager.initialize_session()
            cls.add(clash_manager)

    @classmethod
    def add(cls, clash_manager: ClashManager) -> None:
        cls.clash_managers[clash_manager.id] = clash_manager

    @classmethod
    def get(cls, reserve: bool = False) -> ClashManager:
        for clash_manager in cls.clash_managers.values():
            if reserve:
                if clash_manager.reserved:
                    continue
                clash_manager.reserved = True

            return clash_manager
        
        raise ClashError("There is no clash managers available")

    async def post(self, end_point: str, data, headers: dict[str, str] = {}) -> aiohttp.ClientResponse:
        response = await self.session.post("https://www.codingame.com/" + end_point, data = data, headers = headers)
        return response

    async def new_clash(self, modes: list[str], langs: list[str]) -> str:
        data = [
            self.id,
            langs,
            modes
        ]

        request = await self.post('services/ClashOfCode/createPrivateClash', data = json.dumps(data), headers = json_headers)

        return (await request.json())['publicHandle']

    async def start(self, match_id: str) -> None:
        data = [
            self.id,
            match_id
        ]
        
        game_infos = await self.get_game_infos(match_id)

        time_left = game_infos["startTimestamp"] / 1000 - time()

        if time_left < 10:
            raise ClashError("Game is already starting!")

        response = await self.post('services/ClashOfCode/startClashByHandle', data = json.dumps(data), headers = json_headers)
        # TODO: check if it actually started

    async def invite_user(self, user_id: str, match_id: str) -> dict[str, Any] | None:

        data = [
            self.id,
            user_id,
            match_id
        ]

        response = await self.post("services/ClashOfCode/inviteCodingamers", data = json.dumps(data), headers = json_headers)
        # TODO: check if it actually invited the user
        
    async def invite_users(self, users_ids: list[str], match_id: str) -> list[dict[str, Any]] | None:
        tasks = []
        for user_id in users_ids:
            tasks.append(asyncio.create_task(self.invite_user(user_id, match_id)))
        
        results = []
        for task in await asyncio.gather(*tasks):
            results.append(task)

        return results

    async def get_game_infos(self, match_id: str) -> dict[str, Any]:
        response = await self.post("services/ClashOfCode/findClashByHandle", json.dumps([match_id]), headers = json_headers)
        return await response.json()

    async def submit(self, match_id: str, code: str, language: str, share: bool = True) -> dict[str, Any]:
        game_infos = await self.get_game_infos(match_id)

        for player in game_infos["players"]:

            if player["codingamerId"] != self.id:
                continue

            if player["testSessionStatus"] != "READY":
                raise ClashError("Already submitted!")
            
            submit_response = await self.post("services/TestSession/submit", 
                json.dumps([player["testSessionHandle"], {"code": code, "programmingLanguageId": language}, None]),
                headers = json_headers)
            # TODO: check if it submitted
        
            if share:
                share_response = await self.post("services/ClashOfCode/shareCodinGamerSolutionByHandle",
                    json.dumps([self.id, match_id]),
                    headers = json_headers)
                # TODO: check if it shared

            return await submit_response.json()
    
        raise ClashError("Can't find bot in the clash!")

    async def get_coc_leaderboad_page(self, page: int) -> dict[str, Any]:
        response = await self.post(
            "services/Leaderboards/getClashLeaderboard",
            data = json.dumps([page, {}, None, True, "global", None]),
            headers = json_headers)
        
        return await response.json()

    async def get_coc_players_from_ld(self, start_page: int, end_page: int) -> list[dict[str, Any]]:
        tasks = []
        for page in range(start_page,end_page+1):
            tasks.append(asyncio.create_task(self.get_coc_leaderboad_page(page)))

        players = []
        for page in await asyncio.gather(*tasks):
            players.extend(page["users"])
        return players
    
    async def search_user(self, username: str) -> dict[str, Any]:
        response = await self.post(
            "services/search/search",
            data = json.dumps([username, "en", "props.type"]),
            headers = json_headers)
        
        for result in await response.json():
            if result["type"] == "USER" and result["name"] == username:
                return result
            
        raise ClashError("Username is incorrect")
    
    async def get_user_info(self, public_handle: str) -> dict[str, Any]:
        response = await self.post(
            "services/CodinGamer/findCodingamePointsStatsByHandle",
            data = json.dumps([public_handle]),
            headers = json_headers
        )
        
        return await response.json()