import os, time
CACHE_DIRS = ["/tmp/cache", "/tmp/preview_models", "/tmp/temp_uploads"]
EXPIRATION_SECONDS = 60 * 60 * 24  # 1 day

def cleanup():
    now = time.time()
    for directory in CACHE_DIRS:
        for f in os.listdir(directory):
            path = os.path.join(directory, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > EXPIRATION_SECONDS:
                os.remove(path)

if __name__ == "__main__":
    cleanup()