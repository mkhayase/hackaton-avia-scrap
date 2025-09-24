import uvicorn
from fastapi import FastAPI

app = FastAPI()

def main():
    uvicorn.run(app)


main()
