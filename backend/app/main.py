from fastapi import FastAPI, status
from routes.script_routes import router

app = FastAPI()
app.include_router(router)

@app.get("/", status_code=status.HTTP_201_CREATED)
def home():
    return {"msg":"API funcionando"}