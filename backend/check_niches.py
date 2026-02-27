from app.db import sync_engine
from sqlmodel import Session, select
from app.models.niche import Niche
import os

with Session(sync_engine) as session:
    niches = session.exec(select(Niche)).all()
    for n in niches:
        print(f"ID: {n.id} | Name: {n.name} | Slug: {n.slug}")
