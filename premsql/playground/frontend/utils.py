import re 
import os 
import pandas as pd 
import kagglehub
import sqlite3
from pathlib import Path
from platformdirs import user_cache_dir
from premsql.logger import setup_console_logger

logger = setup_console_logger("[FRONTEND-UTILS]")

def _is_valid_kaggle_id(kaggle_id: str) -> bool:
    pattern = r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, kaggle_id))

def download_from_kaggle(kaggle_dataset_id: str):
    path = kagglehub.dataset_download(handle=kaggle_dataset_id)
    return path 

def _migrate_to_sqlite(csv_folder: Path, sqlite_db_path: Path) -> Path:
    """Common migration logic for both Kaggle and local CSV uploads."""
    conn = sqlite3.connect(sqlite_db_path)
    try:
        for csv_file in csv_folder.glob('*.csv'):
            table_name = csv_file.stem
            df = pd.read_csv(csv_file)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            logger.info(f"Migrated {csv_file.name} to table '{table_name}'")
        
        logger.info(f"Successfully migrated all CSV files to {sqlite_db_path}")
        return sqlite_db_path
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        conn.close()

def migrate_from_csv_to_sqlite(
    folder_containing_csvs: str, 
    session_name: str
) -> Path:
    sqlite_db_folder = Path(user_cache_dir()) / "premsql" / "kaggle"
    os.makedirs(sqlite_db_folder, exist_ok=True)
    sqlite_db_path = sqlite_db_folder / f"{session_name}.sqlite"
    return _migrate_to_sqlite(Path(folder_containing_csvs), sqlite_db_path)

def migrate_local_csvs_to_sqlite(
    uploaded_files: list,
    session_name: str
) -> Path:
    cache_dir = Path(user_cache_dir())
    csv_folder = cache_dir / "premsql" / "csv_uploads" / session_name
    sqlite_db_folder = cache_dir / "premsql" / "csv_uploads"
    
    os.makedirs(csv_folder, exist_ok=True)
    os.makedirs(sqlite_db_folder, exist_ok=True)
    
    sqlite_db_path = sqlite_db_folder / f"{session_name}.sqlite"
    
    # Save uploaded files to CSV folder
    for uploaded_file in uploaded_files:
        file_path = csv_folder / uploaded_file.name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
    
    return _migrate_to_sqlite(csv_folder, sqlite_db_path)