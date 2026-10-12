from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User, ProfileUser, CondoUnit, Charger
from schemas import (UserCreate, UserOut, LoginIn, TokenOut, UnitCreate, UnitOut,
                     ChargerCreate, ChargerOut)
from security import hash_password, verify_password, create_token, get_current_user, require_manager

router = APIRouter(tags=["Usuarios e cadastros"])


def _create_user(db: Session, body: UserCreate, profile: ProfileUser) -> User:
    if db.get(CondoUnit, body.unit_id) is None:
        raise HTTPException(404, "Unidade nao encontrada")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "Email ja cadastrado")
    user = User(name=body.name, email=body.email, unit_id=body.unit_id, profile=profile,
                password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return user


@router.post("/usuarios", response_model=UserOut, status_code=201)
def register_resident(body: UserCreate, db: Session = Depends(get_db)):
    """Cadastro publico: sempre cria um Morador."""
    return UserOut.from_user(_create_user(db, body, ProfileUser.Morador))


@router.post("/usuarios/gestor", response_model=UserOut, status_code=201)
def register_manager(body: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    return UserOut.from_user(_create_user(db, body, ProfileUser.Gestor))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    # Mesma mensagem para email inexistente e senha errada (nao revela qual deu errado).
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email ou senha invalidos")
    return TokenOut(access_token=create_token(user))


@router.get("/usuarios/eu", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.from_user(user)


@router.post("/unidades", response_model=UnitOut, status_code=201)
def create_unit(body: UnitCreate, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    unit = CondoUnit(unit=body.unit)
    db.add(unit)
    db.commit()
    return unit


@router.get("/unidades", response_model=list[UnitOut])
def list_units(db: Session = Depends(get_db)):
    return db.scalars(select(CondoUnit).order_by(CondoUnit.id)).all()


@router.post("/carregadores", response_model=ChargerOut, status_code=201)
def create_charger(body: ChargerCreate, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    if db.get(Charger, body.id):
        raise HTTPException(409, "Carregador ja cadastrado")
    charger = Charger(id=body.id)
    db.add(charger)
    db.commit()
    return charger


@router.get("/carregadores", response_model=list[ChargerOut])
def list_chargers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Charger).order_by(Charger.id)).all()
