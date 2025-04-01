from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Query, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError, \
    field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from database import SensorMetric, get_db, create_tables
from natural_query_handler import parse_nl_query

app = FastAPI(title="Weather Sensor API")

# Create the tables at startup
create_tables()


# Pydantic model for sensor data ingestion and inline/in model validation.
class SensorMetricCreate(BaseModel):
    sensor_id: int = Field(..., gt=0,
                           description="Unique ID of the sensor. "
                                       "Must be a positive integer.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature: Optional[float] = Field(None,
                                         description="Temperature reading "
                                                     "in Celsius.")
    humidity: Optional[float] = Field(None,
                                      description="Humidity percentage.")
    wind_speed: Optional[float] = Field(None,
                                        description="Wind speed in km/h.")

    # Validator for sensor_id field:
    @field_validator("sensor_id", mode="after")
    @classmethod
    def validate_sensor_id(cls, sensor_id) -> Optional[int]:
        if sensor_id is None:
            raise ValueError("Sensor ID must be provided.")
        if not isinstance(sensor_id, int):
            raise ValueError("Sensor ID must be an integer.")
        return sensor_id


@app.post("/metrics", status_code=201)
def add_metric(metric: SensorMetricCreate, db=Depends(get_db)):
    """
    Endpoint to ingest a new sensor metric.
    """
    try:
        db_metric = SensorMetric(**metric.dict())
        # Update timestamp to current UTC time
        db_metric.timestamp = datetime.utcnow()
        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)
        return {"message": "Metric added successfully", "id": db_metric.id}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500,
                            detail="Failed to add sensor metric due to "
                                   "a database error.")

    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422,
                            detail=f"Validation error: {e.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error "
                                                    "occurred while adding "
                                                    "the sensor metric.")


@app.get("/metrics/query")
def query_metrics(
        input_query: str = Query(None,
                                 description="Natural Input Query"),
        db=Depends(get_db)):
    """
    Endpoint to query the database using a natural language query.
    :param input_query: string value of the natural language query.
    :param db: database session.
    :return: json object with the query result or error message.
    """

    print("Input User Query: ", input_query)

    # Execute the SQL query.
    try:
        llm_result = parse_nl_query(input_query)
    except Exception as e:
        raise HTTPException(status_code=400,
                            detail="Error parsing the natural language query.")

    if not llm_result.valid_query:
        raise HTTPException(
            status_code=400,
            detail="Invalid SQL query generated "
                   "from the natural language input."
        )
    print("Query generated: ", llm_result.query)

    # Execute the SQL query and convert results to a DataFrame.
    try:
        result = db.execute(text(llm_result.query))
        data = result.fetchall()
        columns = result.keys()
        df = pd.DataFrame(data, columns=columns)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500, detail="Database error while executing the query."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during query execution."
        )

    return {"data": df.to_dict(orient="records")}
