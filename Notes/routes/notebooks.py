from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from sqlalchemy import select
from models import Notebook
from schemas import NotebookCreate, Notebook as NotebookSchema
from utils.auth import get_current_user_id

router = APIRouter()

@router.post("/", response_model=NotebookSchema)
async def create_notebook(
    data: NotebookCreate,
    session: AsyncSession = Depends(get_session),
    request: Request = None
):
    user_id = get_current_user_id(request)
    notebook = Notebook(title=data.title, user_id=user_id)
    session.add(notebook)
    await session.commit()
    await session.refresh(notebook)
    return notebook

@router.get("/", response_model=list[NotebookSchema])
async def list_notebooks(
    session: AsyncSession = Depends(get_session),
    request: Request = None
):
    user_id = get_current_user_id(request)
    q = await session.execute(
        select(Notebook).where(Notebook.user_id == user_id)
    )
    return q.scalars().all()

@router.patch("/{notebook_id}", response_model=NotebookSchema)
async def update_notebook(
    notebook_id: str,
    data: NotebookCreate,
    session: AsyncSession = Depends(get_session),
    request: Request = None
):
    user_id = get_current_user_id(request)
    q = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user_id)
    )
    notebook = q.scalar_one_or_none()
    if not notebook:
        raise HTTPException(404, "Notebook not found")
    notebook.title = data.title
    await session.commit()
    return notebook

@router.delete("/{notebook_id}", status_code=204)
async def delete_notebook(
    notebook_id: str,
    session: AsyncSession = Depends(get_session),
    request: Request = None
):
    user_id = get_current_user_id(request)
    q = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user_id)
    )
    notebook = q.scalar_one_or_none()
    if not notebook:
        raise HTTPException(404, "Notebook not found")
    await session.delete(notebook)
    await session.commit()
    return None
