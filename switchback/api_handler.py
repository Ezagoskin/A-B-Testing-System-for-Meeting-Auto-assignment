import aiohttp
import urllib

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fancy_decorators import api_retry_decorator

class RegionSettingsAPIClient:
    ui_access_token: Optional[str] = None
    ui_access_token_url: str = 'https://delivery.tcsbank.ru/auth/token?client_id=agent-scheduler&grant_type=password&password={password}&scope=openid&username={login}'
    ui_access_token_expiration_date: Optional[datetime] = None

    back_access_token: Optional[str] = None
    back_access_token_url: str = 'https://delivery.tcsbank.ru/auth/token?client_id=ags_api_client&grant_type=password&password={password}&scope=openid&username={login}'
    back_access_token_expiration_date: Optional[datetime] = None
    
    get_settings_url: str = 'https://agents.tcsbank.ru/ws/regions/{region_id}'
    set_settings_url: str = "https://delivery.tcsbank.ru/api/v2/regions/settings"

    def __init__(self, ui_login: str, ui_password: str, back_login: str, back_password: str):
        self.ui_login = urllib.parse.quote(ui_login)
        self.ui_password = urllib.parse.quote(ui_password)
        self.back_login = urllib.parse.quote(back_login)
        self.back_password = urllib.parse.quote(back_password)

        self.ui_access_token_url = self.ui_access_token_url.format(login=self.ui_login, password=self.ui_password)
        self.back_access_token_url = self.back_access_token_url.format(login=self.back_login, password=self.back_password)

    @api_retry_decorator(10, 1)
    async def ensure_ui_access_token(self, session: aiohttp.ClientSession, forced: bool = False) -> None:
        if not (forced or self.ui_access_token_expiration_date is None or self.ui_access_token_expiration_date < datetime.utcnow()):
            return
            
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        async with session.post(self.ui_access_token_url, headers=headers, raise_for_status=True) as response:
            response_json = await response.json()
            
            self.ui_access_token = response_json['access_token']
            self.ui_access_token_expiration_date = datetime.utcnow() + timedelta(seconds=response_json['expires_in'] - 60)

    @api_retry_decorator(10, 1)
    async def ensure_back_access_token(self, session: aiohttp.ClientSession, forced: bool = False) -> None:
        if not (forced or self.back_access_token_expiration_date is None or self.back_access_token_expiration_date < datetime.utcnow()):
            return
            
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        async with session.post(self.back_access_token_url, headers=headers, raise_for_status=True) as response:
            response_json = await response.json()
            
            self.back_access_token = response_json['access_token']
            self.back_access_token_expiration_date = datetime.utcnow() + timedelta(seconds=response_json['expires_in'] - 60)

    @api_retry_decorator(10, 1)
    async def get_settings(self, session: aiohttp.ClientSession, region_id: str) -> Dict[str, Any]:
        await self.ensure_ui_access_token(session)
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {self.ui_access_token}'
        }

        async with session.get(self.get_settings_url.format(region_id=region_id), headers=headers, raise_for_status=True) as response:
            return await response.json()

    @api_retry_decorator(10, 1)
    async def set_settings(self, session: aiohttp.ClientSession, settings: List[Dict[str, Any]]) -> Dict[str, Any]:
        await self.ensure_back_access_token(session)
        
        headers = {
            'accept': '*/*',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.back_access_token}'
        }

        async with session.put(self.set_settings_url, headers=headers, json=settings, raise_for_status=True) as response:
            return {'response_text': await response.text()}

