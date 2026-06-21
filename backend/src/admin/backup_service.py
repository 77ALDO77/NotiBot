import os
import subprocess
import shutil
import glob
import gzip
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from fastapi import HTTPException
from src.core.config import settings

# Ruta del directorio de copias de seguridad unificado (NotiBot/backups)
backend_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)
if os.path.basename(backend_root) == "backend":
    PROJECT_ROOT = os.path.dirname(backend_root)
else:
    PROJECT_ROOT = backend_root

BACKUPS_DIR = os.path.join(PROJECT_ROOT, "backups")

def get_db_connection_params():
    """
    Parsea la variable DATABASE_URL para obtener parámetros individuales de conexión.
    """
    db_url = settings.DATABASE_URL
    if "postgresql+asyncpg://" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    
    # Manejar socket Unix si está definido en la query (?host=/path/to/socket)
    query_params = parse_qs(parsed.query)
    if "host" in query_params:
        host = query_params["host"][0]
        
    return {
        "host": host,
        "port": port,
        "username": parsed.username or "notibot",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/") or "notibot",
    }

def get_pg_dump_cmd(params) -> tuple[list[str], dict]:
    """
    Retorna el comando para ejecutar pg_dump y el entorno a utilizar.
    Intenta usar la herramienta local en el host. Si no existe, intenta usar
    docker exec sobre el contenedor 'notibot-postgres' si está en ejecución.
    """
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]

    if shutil.which("pg_dump"):
        cmd = ["pg_dump"]
        if params["host"]:
            cmd.extend(["-h", str(params["host"])])
        if params["port"]:
            cmd.extend(["-p", str(params["port"])])
        if params["username"]:
            cmd.extend(["-U", str(params["username"])])
        if params["database"]:
            cmd.extend(["-d", str(params["database"])])
        return cmd, env

    # Fallback a Docker exec en notibot-postgres
    if shutil.which("docker"):
        try:
            res = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if "notibot-postgres" in res.stdout:
                cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={params['password']}", "notibot-postgres", "pg_dump"]
                cmd.extend(["-U", params["username"]])
                cmd.extend(["-d", params["database"]])
                return cmd, env
        except Exception:
            pass

    raise HTTPException(
        status_code=500,
        detail="La herramienta 'pg_dump' no está instalada localmente ni se detectó el contenedor docker 'notibot-postgres' en ejecución para realizar el fallback."
    )

def get_psql_cmd(params, sql_command: str = None) -> tuple[list[str], dict]:
    """
    Retorna el comando para ejecutar psql y el entorno a utilizar.
    Intenta usar la herramienta local en el host. Si no existe, intenta usar
    docker exec sobre el contenedor 'notibot-postgres'.
    """
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]

    if shutil.which("psql"):
        cmd = ["psql"]
        if params["host"]:
            cmd.extend(["-h", str(params["host"])])
        if params["port"]:
            cmd.extend(["-p", str(params["port"])])
        if params["username"]:
            cmd.extend(["-U", str(params["username"])])
        if params["database"]:
            cmd.extend(["-d", str(params["database"])])
        if sql_command:
            cmd.extend(["-c", sql_command])
        return cmd, env

    # Fallback a Docker exec en notibot-postgres
    if shutil.which("docker"):
        try:
            res = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if "notibot-postgres" in res.stdout:
                cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={params['password']}", "notibot-postgres", "psql"]
                cmd.extend(["-U", params["username"]])
                cmd.extend(["-d", params["database"]])
                if sql_command:
                    cmd.extend(["-c", sql_command])
                return cmd, env
        except Exception:
            pass

    raise HTTPException(
        status_code=500,
        detail="La herramienta 'psql' no está instalada localmente ni se detectó el contenedor docker 'notibot-postgres' en ejecución para realizar el fallback."
    )

def create_backup_file() -> str:
    """
    Crea un dump completo de la base de datos y lo guarda comprimido en formato .sql.gz.
    """
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notibot_backup_{timestamp}.sql.gz"
    file_path = os.path.join(BACKUPS_DIR, filename)
    
    params = get_db_connection_params()
    cmd, env = get_pg_dump_cmd(params)
        
    try:
        # Ejecutar pg_dump/docker exec y comprimir el flujo directamente usando el módulo gzip de Python
        with gzip.open(file_path, "wb") as f_out:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Leer en bloques e ir escribiendo
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                f_out.write(chunk)
                
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                if os.path.exists(file_path):
                    os.remove(file_path)
                error_msg = stderr.decode(errors="ignore") if stderr else "Error desconocido"
                raise Exception(f"pg_dump falló con código {process.returncode}: {error_msg}")
                
        return filename
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error creando copia de seguridad: {str(e)}")

def restore_backup_file(file_path: str):
    """
    Restaura la base de datos a partir de un archivo .sql.gz.
    Limpia (DROP SCHEMA public CASCADE) el esquema público para evitar cualquier colisión.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="El archivo de copia de seguridad no existe.")
        
    params = get_db_connection_params()
    
    # 1. Comando SQL para limpiar completamente el esquema público
    clean_sql = (
        f"DROP SCHEMA public CASCADE; "
        f"CREATE SCHEMA public; "
        f"GRANT ALL ON SCHEMA public TO public; "
        f"GRANT ALL ON SCHEMA public TO {params['username']};"
    )
    
    clean_cmd, env = get_psql_cmd(params, clean_sql)
    
    try:
        # Ejecutar limpieza del esquema
        clean_proc = subprocess.run(
            clean_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        if clean_proc.returncode != 0:
            raise Exception(f"Limpieza de base de datos falló: {clean_proc.stderr.decode(errors='ignore')}")
            
        # 2. Comando para restaurar los datos
        restore_cmd, env = get_psql_cmd(params)
            
        restore_proc = subprocess.Popen(
            restore_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        # Decomprimir flujo de gzip e inyectarlo en stdin de psql
        with gzip.open(file_path, "rb") as f_in:
            while True:
                chunk = f_in.read(65536)
                if not chunk:
                    break
                restore_proc.stdin.write(chunk)
                
        stdout, stderr = restore_proc.communicate()
        if restore_proc.returncode != 0:
            error_msg = stderr.decode(errors="ignore") if stderr else "Error desconocido"
            raise Exception(f"psql falló con código {restore_proc.returncode}: {error_msg}")
            
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restaurando base de datos: {str(e)}")

def list_backups_files() -> list[dict]:
    """
    Retorna la lista de archivos de copias de seguridad disponibles en disco.
    """
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    files = glob.glob(os.path.join(BACKUPS_DIR, "notibot_backup_*.sql.gz"))
    backups = []
    
    for f in files:
        stat = os.stat(f)
        filename = os.path.basename(f)
        
        try:
            # Extraer fecha del nombre: notibot_backup_YYYYMMDD_HHMMSS.sql.gz
            date_str = filename.replace("notibot_backup_", "").replace(".sql.gz", "")
            dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
        backups.append({
            "filename": filename,
            "size_bytes": stat.st_size,
            "created_at": formatted_date
        })
        
    backups.sort(key=lambda x: x["filename"], reverse=True)
    return backups

def delete_backup_file(filename: str):
    """
    Elimina físicamente una copia de seguridad.
    """
    # Sanitizar el nombre del archivo para evitar Directory Traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(BACKUPS_DIR, safe_filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

def get_backup_absolute_path(filename: str) -> str:
    """
    Obtiene la ruta absoluta y segura para un archivo de respaldo.
    """
    safe_filename = os.path.basename(filename)
    return os.path.join(BACKUPS_DIR, safe_filename)
