"""AuditLogger - writes who did what to the audit_logs table."""
import json
import socket

from core.session import SessionManager
from repositories import AuditLogRepository


def _local_ip() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


class AuditLogger:
    _ip = None

    def __init__(self):
        self.repo = AuditLogRepository()
        self.session = SessionManager.get_instance()
        if AuditLogger._ip is None:
            AuditLogger._ip = _local_ip()

    def log(self, action, table, record_id=None, old=None, new=None, cursor=None, user_id=None):
        if user_id is None and self.session.is_logged_in():
            user_id = self.session.current_user["user_id"]

        def dump(value):
            return None if value is None else json.dumps(value, default=str, ensure_ascii=False)

        self.repo.create(user_id, action, table, record_id, dump(old), dump(new), self._ip, cursor)
