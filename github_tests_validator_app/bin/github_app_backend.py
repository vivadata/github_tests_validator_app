from typing import cast

import logging
import os
import traceback

import uvicorn
from fastapi import FastAPI, Request
from github_tests_validator_app.bin.github_event_process import run

app = FastAPI()


@app.post("/")
async def main(request: Request) -> None:
    try:
        payload = await request.json()
        run(payload)
    except:
        formatted_exception = traceback.format_exc()
        logging.error(formatted_exception)


def launch_app():
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=cast(int, os.environ.get("PORT", 8080)),
        log_level="info",
    )
