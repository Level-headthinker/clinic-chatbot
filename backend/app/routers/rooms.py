from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.room import Room
from app.models.user import User
from app.services.auth import require_admin_user

router = APIRouter(prefix="/rooms", tags=["Rooms"])


class RoomCreate(BaseModel):
    name: str


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


def _fmt(r):
    return {
        "id": str(r.id),
        "name": r.name,
        "is_occupied": r.is_occupied,
        "current_appointment_id": str(r.current_appointment_id) if r.current_appointment_id else None,
        "is_active": r.is_active,
    }


@router.get("/")
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    q = db.query(Room).filter(
        Room.tenant_id == current_user.tenant_id,
        Room.is_active == True,
    )
    if current_user.branch_id:
        q = q.filter(Room.branch_id == current_user.branch_id)
    return [_fmt(r) for r in q.order_by(Room.name).all()]


@router.post("/")
def create_room(
    data: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    room = Room(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        name=data.name.strip(),
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return _fmt(room)


@router.put("/{room_id}")
def update_room(
    room_id: str,
    data: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    room = db.query(Room).filter(
        Room.id == room_id,
        Room.tenant_id == current_user.tenant_id,
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if data.name is not None:
        room.name = data.name.strip()
    if data.is_active is not None:
        room.is_active = data.is_active
    db.commit()
    return _fmt(room)


@router.delete("/{room_id}")
def delete_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    room = db.query(Room).filter(
        Room.id == room_id,
        Room.tenant_id == current_user.tenant_id,
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.is_active = False
    db.commit()
    return {"message": "Room removed."}
