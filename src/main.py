from fastapi import FastAPI
from api.routers.pipeline import router

app = FastAPI()

app.include_router(router)

def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
if __name__ == "__main__":
    main()