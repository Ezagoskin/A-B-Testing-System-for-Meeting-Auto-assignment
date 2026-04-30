import logging
import asyncio
import traceback
import functools

from logging.config import dictConfig
from typing import Any, Callable
from quart import request

dictConfig({
    'version': 1,
    'formatters': {
        "json": {
            '()': 'logging_json.JSONFormatter',
            'fields': {
                "env": "prod",
                "system": "autoplanner-switchback-api",
                "inst": "10.235.6.232",
                "@timestamp": "asctime",
                "level": "levelname",
                "message": "message"
            },
            'datefmt': '%Y-%m-%dT%H:%M:%S%z'
        }
    },
    'handlers': {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "service.log",
            "formatter": "json",
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
})

def fancy_api_logger(function: Callable) -> Callable:
    function_name = function.__name__

    if asyncio.iscoroutinefunction(function):
        @functools.wraps(function)
        async def async_wrapper(*args, **kwargs) -> Any:
            data = await request.get_json()

            route_name = request.path
            method_name = request.method

            logging.info(
                f'Request arguments: {data}', 
                extra = {
                    'op': f'{method_name} {route_name}', 
                    'method': function_name, 
                }
            )

            try:
                response = await function(*args, **kwargs)

                logging.info(
                    f'Response payload: {await response.get_json()}',
                    extra = {
                        'op': f'{method_name} {route_name}', 
                        'method': function_name, 
                        'responseStatusCode': int(response.status_code),
                    }
                )

                return response
            except Exception:
                logging.error(
                    f'Response payload: {traceback.format_exc()}',
                    extra = {
                        'op': f'{method_name} {route_name}', 
                        'method': function_name, 
                        'responseStatusCode': 500, 
                    }
                )

        return async_wrapper

    raise NotImplementedError 

def fancy_logger(function: Callable) -> Callable:
    function_name = function.__name__

    if asyncio.iscoroutinefunction(function):
        @functools.wraps(function)
        async def async_wrapper(*args, **kwargs) -> Any:
            logging.info(
                f'Function arguments: args = {args}, kwargs = {kwargs}', 
                extra = {
                    'method': function_name, 
                }
            )

            try:
                result = await function(*args, **kwargs)

                logging.info(
                    f'Function result: {result}',
                    extra = {
                        'method': function_name,
                    }
                )

                return result
            except Exception:
                logging.error(
                    f'Function exception traceback: {traceback.format_exc()}',
                    extra = {
                        'method': function_name, 
                    }
                )

        return async_wrapper

    raise NotImplementedError 
