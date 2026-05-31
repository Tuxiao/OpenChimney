from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, has_super_admin_role
from ..models import MessageAttachment, User

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


def is_admin(user: User) -> bool:
    return has_super_admin_role(user)


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> FileResponse:
    attachment = db.get(MessageAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")

    owner_id = attachment.message.conversation.owner_user_id
    if owner_id != user.id and not is_admin(user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")

    storage_root = Path(request.app.state.config.artifact_storage_dir).resolve()
    file_path = (storage_root / str(attachment.id) / attachment.file_name).resolve()
    if not file_path.is_file() or storage_root not in file_path.parents:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment file not found")

    return FileResponse(
        file_path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.file_name,
    )
