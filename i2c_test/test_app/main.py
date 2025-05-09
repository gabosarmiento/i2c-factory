from fastapi import FastAPI
import models
from database import engine
from config import settings
from routers import users, items

# create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TestApp")

# include your routers
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(items.router, prefix=settings.API_PREFIX)

@app.get("/")
def read_root():
    return {"message": "Welcome to TestApp!"}
