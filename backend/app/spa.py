from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, directory: Path) -> None:
    """Sirve el frontend compilado desde el mismo origen que la API (cookies sin dominios cruzados)."""
    root = directory.resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404)
        file = (root / path).resolve()
        if path and file.is_file() and root in file.parents:  # no salir de la carpeta
            return FileResponse(file)
        return FileResponse(root / "index.html")  # rutas de React Router
