import os
import shutil
import tempfile
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from src.admin import backup_service

router = APIRouter(tags=["admin-backups"])

@router.post("/create")
async def create_backup():
    """
    Crea una copia de seguridad y la guarda localmente.
    """
    filename = backup_service.create_backup_file()
    return {"status": "success", "filename": filename}

@router.get("/list")
async def list_backups():
    """
    Lista todos los archivos de respaldo disponibles en el servidor.
    """
    return backup_service.list_backups_files()

@router.get("/download/{filename}")
async def download_backup(filename: str):
    """
    Descarga un archivo de respaldo específico.
    """
    path = backup_service.get_backup_absolute_path(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="El archivo de copia de seguridad no existe.")
    return FileResponse(
        path,
        media_type="application/gzip",
        filename=filename
    )

@router.post("/restore/upload")
async def restore_uploaded_backup(file: UploadFile = File(...)):
    """
    Sube un archivo de copia de seguridad (.sql.gz) y lo restaura inmediatamente.
    """
    if not file.filename.endswith(".sql.gz"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Debe terminar en .sql.gz")
        
    # Guardar en archivo temporal en el servidor para realizar la restauración
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sql.gz") as temp_file:
        temp_path = temp_file.name
        try:
            shutil.copyfileobj(file.file, temp_file)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"Error al guardar el archivo subido: {str(e)}")
            
    try:
        backup_service.restore_backup_file(temp_path)
        return {"status": "success", "message": "Base de datos restaurada correctamente a partir del archivo subido."}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/restore/local/{filename}")
async def restore_local_backup(filename: str):
    """
    Restaura la base de datos a partir de una copia de seguridad guardada localmente en el servidor.
    """
    path = backup_service.get_backup_absolute_path(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="El archivo de copia de seguridad no existe.")
    
    backup_service.restore_backup_file(path)
    return {"status": "success", "message": f"Copia de seguridad '{filename}' restaurada correctamente."}

@router.delete("/{filename}")
async def delete_backup(filename: str):
    """
    Elimina un archivo de respaldo específico.
    """
    success = backup_service.delete_backup_file(filename)
    if not success:
        raise HTTPException(status_code=404, detail="Copia de seguridad no encontrada.")
    return {"status": "success", "message": f"Copia de seguridad '{filename}' eliminada correctamente."}
