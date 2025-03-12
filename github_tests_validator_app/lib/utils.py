from typing import Any, Dict, List, Optional

import re
import hashlib
import logging
import random
from datetime import datetime

from github import ContentFile, GithubException
from github_tests_validator_app.lib.connectors.sqlalchemy_client import User



def get_hash_files(contents: List[ContentFile.ContentFile]) -> str:
    hash = hashlib.sha256()

    for content in contents:
        if content.type == 'file':
            file_content = content.decoded_content  # Gets the file's content as bytes
            logging.info(f"Hashing content for file: {content.path}, Content length: {len(file_content)}")
            hash.update(file_content)
        else:
            logging.info(f"Hashing submodule/directory SHA for: {content.path}, SHA: {content.sha}")
            hash.update(content.sha.encode())

    hash_value = str(hash.hexdigest())
    logging.info(f"Generated hash value: {hash_value}")
    return hash_value

def init_github_user_from_github_event(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    if not "sender" in data:
        return None

    login = data["sender"]["login"]
    id = data["sender"]["id"]
    url = data["sender"]["url"]
    return dict(id=id, organization_or_user=login, url=url, created_at=datetime.now())


def strip_ansi_escape_codes(text: str) -> str:
    """
    Removes ANSI escape codes from the given text.
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)
