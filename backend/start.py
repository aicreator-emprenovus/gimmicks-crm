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

    should_build = False
    if not static_dir.exists() and frontend_dir.exists():
        should_build = True
    elif static_dir.exists() and frontend_dir.exists():
        # Check if frontend source is newer than build
        src_dir = frontend_dir / "src"
        if src_dir.exists():
            build_index = static_dir / "index.html"
            if build_index.exists():
                build_time = build_index.stat().st_mtime
                for src_file in src_dir.rglob("*"):
                    if src_file.is_file() and src_file.stat().st_mtime > build_time:
                        print(f"Frontend source newer than build: {src_file}")
                        should_build = True
                        break

    if should_build:
        print("Building frontend for production...")
        env = os.environ.copy()
        env["REACT_APP_BACKEND_URL"] = ""
        try:
            subprocess.run(["yarn", "install", "--frozen-lockfile"], cwd=str(frontend_dir), env=env, check=True, timeout=120)
            subprocess.run(["yarn", "build"], cwd=str(frontend_dir), env=env, check=True, timeout=120)
            build_dir = frontend_dir / "build"
            if build_dir.exists():
                import shutil
                if static_dir.exists():
                    shutil.rmtree(str(static_dir))
                shutil.copytree(str(build_dir), str(static_dir))
                print("Frontend built and copied to static_frontend/")
        except Exception as e:
            print(f"Frontend build failed: {e}")

    uvicorn.run("server:app", host="0.0.0.0", port=port)
