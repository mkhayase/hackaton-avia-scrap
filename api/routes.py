from main import app
from fastapi import UploadFile
from services import convert_from_xlsx_to_json


@app.post("/data")
async def raw_data(file: UploadFile):
    return
