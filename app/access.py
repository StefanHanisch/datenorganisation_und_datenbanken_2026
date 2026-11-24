"""Session roles shared by the HTML pages and the JSON APIs."""
from fastapi import HTTPException, Request


def role_of(request: Request) -> str | None:
    role = request.session.get('role')
    return role if role in ('student', 'teacher') else None


def require_access(request: Request, teacher: bool = False) -> str:
    role = role_of(request)
    if role is None:
        raise HTTPException(status_code=401, detail='Bitte zuerst anmelden.')
    if teacher and role != 'teacher':
        raise HTTPException(status_code=403, detail='Nur für die Lehrperson freigegeben.')
    return role
