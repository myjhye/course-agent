"""
pytest 로딩 시 app.config가 먼저 올라가기 전에 더미 API 키를 둔다.
(실제 .env 키가 있으면 setdefault는 덮어쓰지 않음.)
"""

import os

os.environ.setdefault("KSPO_API_KEY", "pytest-dummy-kspo-key")
