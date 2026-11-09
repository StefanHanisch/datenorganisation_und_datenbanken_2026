"""Configuration for a short-lived classroom installation (never use real guest data)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = ''
    student_database_url: str = ''
    session_secret: str = ''
    student_access_code: str = ''
    teacher_access_code: str = ''
    cookie_secure: bool = False
    sql_statement_timeout_ms: int = 4000
    sql_max_rows: int = 100

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
