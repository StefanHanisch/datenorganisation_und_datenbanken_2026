"""Configuration for a short-lived classroom installation (never use real guest data)."""
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db_target import resolve_db_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = ''
    student_database_url: str = ''
    # DB_TARGET=local|azure picks one of these URL sets (see app/db_target.py)
    db_target: str = ''
    local_database_url: str = ''
    local_student_database_url: str = ''
    azure_database_url: str = ''
    azure_student_database_url: str = ''
    session_secret: str = ''
    student_access_code: str = ''
    teacher_access_code: str = ''
    cookie_secure: bool = False
    sql_statement_timeout_ms: int = 4000
    sql_max_rows: int = 100

    @model_validator(mode='after')
    def apply_db_target(self) -> 'Settings':
        if self.db_target.strip():
            urls = {
                'DB_TARGET': self.db_target,
                'LOCAL_DATABASE_URL': self.local_database_url,
                'LOCAL_STUDENT_DATABASE_URL': self.local_student_database_url,
                'AZURE_DATABASE_URL': self.azure_database_url,
                'AZURE_STUDENT_DATABASE_URL': self.azure_student_database_url,
            }
            self.database_url = resolve_db_url(urls, 'DATABASE_URL')
            self.student_database_url = resolve_db_url(urls, 'STUDENT_DATABASE_URL')
        return self

    def check_runtime(self) -> None:
        if not self.database_url or not self.student_database_url:
            raise RuntimeError('DATABASE_URL and STUDENT_DATABASE_URL are required')
        if len(self.session_secret) < 32:
            raise RuntimeError('SESSION_SECRET must contain at least 32 characters')
        if not self.student_access_code or not self.teacher_access_code:
            raise RuntimeError('Access codes must be configured')
        if self.student_access_code == self.teacher_access_code:
            raise RuntimeError('Student and teacher access codes must differ')
        if not 250 <= self.sql_statement_timeout_ms <= 20000:
            raise RuntimeError('SQL statement timeout must be 250..20000 ms')
        if not 1 <= self.sql_max_rows <= 500:
            raise RuntimeError('SQL max rows must be 1..500')


@lru_cache
def get_settings() -> Settings:
    return Settings()
