import asyncio
import os
from datetime import datetime
from io import BytesIO
from typing import Annotated, Any, Dict

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel
from sqlmodel import func, or_, select

import crud
from api.websocket import manager
from core import deps
from core.config import settings
from core.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from core.logging import logger
from core.security import get_password_hash, verify_password
from core.utils import (
    generate_data_export_email,
    generate_new_account_email,
    send_email,
)
from models.message import Message
from models.user import (
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from services.pd import data_to_csv
from services.storage import upload_to_firebase

# Create a router for users
router = APIRouter()


@router.get("/admin-me")
async def read_admin(admin_user: deps.AdminUser) -> User:
    """
    Get current admin user.
    """
    return admin_user  # type: ignore


@router.get("/me")
async def read_user_me(current_user: deps.CurrentUser) -> UserPublic:
    """
    Get current user.
    """
    return current_user  # type: ignore


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(
    db: SessionDep,
    name: str = "",
    page: int = Query(default=1, gt=0),
    per_page: int = Query(default=20, le=100),
) -> Any:
    """
    Retrieve users.
    """

    query = {"firstname": name, "lastname": name}
    filters = crud.user.build_query(query)

    count_statement = select(func.count()).select_from(User)
    if filters:
        count_statement = count_statement.where(or_(*filters))
    total_count = db.exec(count_statement).one()

    users = crud.user.get_multi(
        db=db,
        filters=filters,
        per_page=per_page,
        offset=(page - 1) * per_page,
    )

    total_pages = (total_count // per_page) + (total_count % per_page > 0)

    return UsersPublic(
        data=users,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_count=total_count,
    )


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, db: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.user.get_user_by_email(db=db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.user.create(db=db, user_create=user_in)
    if settings.EMAILS_ENABLED and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, db: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.user.get_user_by_email(db=db, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    current_user = crud.user.update(db=db, db_obj=current_user, obj_in=user_in)
    return current_user


@router.patch("/me/password")
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return {"message": "Password updated successfully"}


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    db: SessionDep,
    user_id: int,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = db.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.user.get_user_by_email(db=db, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = crud.user.update(db=db, db_obj=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(db: SessionDep, current_user: CurrentUser, user_id: int) -> Message:
    """
    Delete a user.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    db.delete(user)
    db.commit()
    return Message(message="User deleted successfully")


class UploadStatus(BaseModel):
    total_rows: int
    processed_rows: int
    status: str


upload_statuses: Dict[str, UploadStatus] = {}


async def process_file(file, task_id: str, db: SessionDep):
    chunk_size = 100
    try:
        df = pd.read_excel(BytesIO(file))
        total_rows = len(df)
        upload_statuses[task_id] = UploadStatus(
            total_rows=total_rows, processed_rows=0, status="Processing"
        )
        await send_status_update(task_id)

        for i in range(0, total_rows, chunk_size):
            chunk = df.iloc[i : i + chunk_size]
            users = chunk.to_dict("records")
            await crud.user.bulk_upload(db=db, users=users)
            upload_statuses[task_id].processed_rows += len(users)
            await send_status_update(task_id)
            await asyncio.sleep(0.1)  # Allow other tasks to run

        if upload_statuses.get(task_id):
            upload_statuses[task_id].status = "Completed"
        await send_status_update(task_id)
    except Exception as e:
        logger.error(f"Error: {e}")
        if upload_statuses.get(task_id):
            upload_statuses[task_id].status = f"Error: {str(e)}"
            await send_status_update(task_id)


async def send_status_update(task_id: str):
    await manager.broadcast(id=task_id, data=upload_statuses.get(task_id).model_dump())


@router.post("/excel/{task_id}")
async def upload_products(
    file: Annotated[UploadFile, File()],
    batch: Annotated[str, Form()],
    task_id: str,
    db: SessionDep,
    background_tasks: BackgroundTasks,
):
    if file is None:
        logger.error("Invalid file provided")
        raise HTTPException(status_code=422, detail="No file provided")

    size_in_mb = file.size / 1024 / 1024
    if size_in_mb > 1.5:
        logger.error("Uploaded file is greater than 1.5MB")
        raise HTTPException(
            status_code=422, detail="File size should not be more than 1.5MB"
        )

    contents = await file.read()
    background_tasks.add_task(process_file, contents, task_id, db)
    return {"batch": batch, "message": "File upload started"}


@router.post("/export")
async def export_users(current_user: CurrentUser, db: SessionDep, bucket: deps.Storage):
    try:
        users = db.exec(select(User))
        # Get the current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"users_export_{current_date}.csv"
        csv = data_to_csv(items=users, filename=filename)
        file_url = upload_to_firebase(file_path=csv, bucket=bucket)

        # Send download link
        email_data = generate_data_export_email(download_link=file_url)
        send_email(
            email_to=current_user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

        # Clean up
        os.remove(f"./{filename}")
        return {"message": "Export successful", "file_url": file_url}
    except Exception as e:
        logger.error(f"Export users error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
