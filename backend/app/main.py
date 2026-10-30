from fastapi import FastAPI
from  app.routes.script_routes import router

app=FastAPI()
app.include_router(router)

app.get("/")
async def home():
    return {"msg":"APP funcionando"}