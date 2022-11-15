from typing import Any, Dict, List, Optional

import hashlib
from datetime import datetime

from github import ContentFile
from github_tests_validator_app.lib.connectors.sqlalchemy_client import User


def get_hash_files(contents: List[ContentFile.ContentFile]) -> str:
    hash_sum = ""
    for content in contents:
        hash_sum += content.sha
    hash = hashlib.sha256()
    hash.update(hash_sum.encode())
    return str(hash.hexdigest())


def init_github_user_from_github_event(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    if not "sender" in data:
        return None

    login = data["sender"]["login"]
    id = data["sender"]["id"]
    url = data["sender"]["url"]
    return dict(id=id, organization_or_user=login, url=url, created_at=datetime.now())
