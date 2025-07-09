from fastapi import UploadFile, File, FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from generate import generate_keychain_stl
from model import GenerationRequest
import os
import uuid
import trimesh
import shutil
import pathlib
import time
import asyncio
BASE_MODEL_DIR = "base_models"
TEMP_UPLOADS_DIR = "/tmp/temp_uploads"
CACHE_DIR = "/tmp/cache"
PREVIEW_OUTPUT_DIR = "/tmp/preview_models"

CLEANUP_INTERVAL_SECONDS = 60 * 60  # 1 hour
FILE_MAX_AGE_SECONDS = 60 * 60   

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


app = FastAPI()
os.makedirs(PREVIEW_OUTPUT_DIR, exist_ok=True)


# CORS setup: replace with actual domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_file_size(file: UploadFile):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    return content

def cleanup_old_files(directory: str, max_age_seconds: int):
    now = time.time()
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    print(f"Deleted old file: {filepath}")
        except Exception as e:
            print(f"Error cleaning file {filepath}: {e}")

async def periodic_cleanup_task():
    while True:
        print("Running periodic cleanup of temp files...")
        for directory in [TEMP_UPLOADS_DIR, CACHE_DIR]:
            if os.path.exists(directory):
                cleanup_old_files(directory, FILE_MAX_AGE_SECONDS)
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
        for d in [BASE_MODEL_DIR, TEMP_UPLOADS_DIR, CACHE_DIR]:
                os.makedirs(d, exist_ok=True)
        
        # Launch cleanup loop in background
        asyncio.create_task(periodic_cleanup_task())
    
    
@app.post("/generate-stl")
async def generate_stl(req: GenerationRequest):
    try:
        # Check if req.baseModel exists in temp_uploads, otherwise use as is
        temp_base_model_path = str(pathlib.Path("temp_uploads") / req.baseModel)
        if os.path.isfile(temp_base_model_path):
            base_model_path = temp_base_model_path
        else:
            base_model_path = req.baseModel

        file_path = generate_keychain_stl(
            bar_heights=req.barHeights,
            base_model=base_model_path,
            extrusion_height=req.extrusionHeight,
        )
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/sla"  # STL MIME
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-glb")
async def generate_glb(req: GenerationRequest):
    try:
        temp_base_model_path = str(pathlib.Path("temp_uploads") / req.baseModel)
        if os.path.isfile(temp_base_model_path):
            base_model_path = temp_base_model_path
        else:
            base_model_path = req.baseModel

        print("Resolved base model path:", base_model_path)
        if not os.path.isfile(base_model_path):
            raise HTTPException(status_code=404, detail=f"Base model file not found at {base_model_path}")

        stl_path = generate_keychain_stl(
            bar_heights=req.barHeights,
            base_model=base_model_path,
            extrusion_height=req.extrusionHeight,
        )

        # Convert STL to GLB
        mesh = trimesh.load(stl_path)
        glb_path = os.path.join(PREVIEW_OUTPUT_DIR, f"{uuid.uuid4()}.glb")
        mesh.export(glb_path)

        return FileResponse(
            path=glb_path,
            filename=os.path.basename(glb_path),
            media_type="model/gltf-binary"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/upload-base-model")
async def upload_base_model(file: UploadFile = File(...)):
    content = await verify_file_size(file)

    if not file.filename or not file.filename.endswith((".step", ".stp")):
        raise HTTPException(status_code=400, detail="Invalid file extension")

    if not content.startswith(b"ISO-10303-21"):
        raise HTTPException(status_code=400, detail="Invalid STEP content")

    uid = str(uuid.uuid4())
    filename = f"{uid}.step"
    upload_path = os.path.join("temp_uploads", filename)

    os.makedirs("temp_uploads", exist_ok=True)
    with open(upload_path, "wb") as f:
        f.write(content)

    return {"filename": filename}