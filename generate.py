import cadquery as cq
import hashlib
import os

BASE_MODEL_DIR = "base_models"
CACHE_DIR = "/tmp/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def generate_keychain_stl(bar_heights, base_model, extrusion_height):
    key = f"{bar_heights}_{base_model}_{extrusion_height}"
    hashed = hashlib.sha256(key.encode()).hexdigest()
    stl_path = os.path.join(CACHE_DIR, f"{hashed}.stl")
    if os.path.exists(stl_path):
        return stl_path

# Check if full path already provided (e.g., from temp_uploads)
    if os.path.isfile(base_model):
        step_path = base_model
    else:
        step_path = os.path.join(BASE_MODEL_DIR, base_model)

    if not os.path.exists(step_path):
        raise FileNotFoundError(f"Base model not found at: {step_path}")


    model = cq.importers.importStep(step_path)
    curr_bar = 0
    for bar in bar_heights:
        model = (
            model.pushPoints([(15.5 + curr_bar * 1.88, 7.5)])
            .sketch()
            .slot(9 / 5 * bar, 1, 90)
            .finalize()
            .extrude(extrusion_height)
        )
        curr_bar += 1

    cq.exporters.export(model, stl_path, exportType="STL")
    return stl_path
