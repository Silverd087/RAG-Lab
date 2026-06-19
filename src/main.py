from fastapi import FastAPI
from api.pipeline import router
def main():
    app = FastAPI()

    app.include_router(router)
    
    
if __name__ == "__main__":
    main()
