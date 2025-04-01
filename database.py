from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, \
    func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup (SQLite for simplicity)
DATABASE_URL = "sqlite:///./weather.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# Database model representing a sensor reading.
class SensorMetric(Base):
    __tablename__ = "sensor_metrics"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)


def create_tables():
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
