import functools
import asyncio
import aiohttp
import logging

from typing import Callable, Any, Type
from quart import jsonify, request, Response
from pydantic import ValidationError, BaseModel

def api_retry_decorator(max_retries: int = 10, wait_time: int = 1) -> Callable:
    def decorator(function: Callable) -> Callable:
        if not asyncio.iscoroutinefunction(function):
            raise NotImplementedError

        @functools.wraps(function)
        async def wrapper(*args, retry_iterations: int = 0, **kwargs) -> Any:
            try:
                return await function(*args, **kwargs)
            except aiohttp.ClientResponseError as exception:
                if retry_iterations >= max_retries:
                    raise aiohttp.ClientError(f'Client error with status code {exception.status}') from exception

            await asyncio.sleep(wait_time)

            return await wrapper(*args, retry_iterations=retry_iterations + 1, **kwargs)

        return wrapper

    return decorator

def fancy_validate_request(model: Type[BaseModel]) -> Callable:
    def decorator(function: Callable) -> Callable:
        if not asyncio.iscoroutinefunction(function):
            raise NotImplementedError

        @functools.wraps(function)
        async def wrapper(*args: Any, **kwargs: Any) -> Response:
            route_name = request.path
            method_name = request.method
            function_name = function.__name__

            try:
                data = await request.get_json()

                if isinstance(data, dict):
                    model(**data)
                if isinstance(data, list):
                    [model(**item) for item in data]

                if not isinstance(data, dict) and not isinstance(data, list):
                    raise ValidationError

                logging.info(
                    'Request arguments: ' + str(data), 
                    extra = {
                        'op': f'{method_name} {route_name}', 
                        'method': function_name, 
                    }
                )

                return await function(*args, **kwargs)
            except ValidationError:
                logging.error(
                    'Incorrect request payload',
                    extra = {
                        'op': f'{method_name} {route_name}', 
                        'method': function_name, 
                        'responseStatusCode': 500, 
                    }
                ) 

                response = jsonify({"error": "Incorrect request payload"})
                response.status_code = 400

                return response 

        return wrapper

    return decorator
