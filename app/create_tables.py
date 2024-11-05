# create_tables.py
from sqlalchemy import create_engine
from models import Base
from database import DATABASE_URL

# Tạo một Engine đồng bộ
sync_engine = create_engine(DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql"))

# Tạo bảng dựa trên các model
Base.metadata.create_all(bind=sync_engine)
