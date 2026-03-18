import os
import subprocess
import uvicorn
from pathlib import Path

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))

    # Build frontend if not already built (for Railway deployment)
    backend_dir = Path(__file__).parent
    static_dir = backend_dir / "static_frontend"
    frontend_dir = backend_dir.parent / "frontend"
    if not static_dir.exists() and frontend_dir.exists():
        print("Building frontend for production...")
        env = os.environ.copy()
        env["REACT_APP_BACKEND_URL"] = ""
        try:
            subprocess.run(["yarn", "install", "--frozen-lockfile"], cwd=str(frontend_dir), env=env, check=True, timeout=120)
            subprocess.run(["yarn", "build"], cwd=str(frontend_dir), env=env, check=True, timeout=120)
            build_dir = frontend_dir / "build"
            if build_dir.exists():
                import shutil
                shutil.copytree(str(build_dir), str(static_dir))
                print("Frontend built and copied to static_frontend/")
        except Exception as e:
            print(f"Frontend build failed: {e}")

    uvicorn.run("server:app", host="0.0.0.0", port=port)
