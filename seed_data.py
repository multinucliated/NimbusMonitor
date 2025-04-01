import random
from datetime import datetime, timedelta
from database import SessionLocal, SensorMetric, create_tables


def seed_database():
    # Create tables if they don't exist yet
    create_tables()

    session = SessionLocal()
    sensor_ids = [1, 2, 3, 4, 5]  # Example sensor IDs

    # Define the time range: last 3 months (approximately 90 days)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=90)

    record_count = 0
    current_time = start_time

    # Loop through each 30-minute interval from start_time to end_time
    while current_time <= end_time:
        # For each sensor, add a record for the current timestamp
        for sensor in sensor_ids:
            record = SensorMetric(
                sensor_id=sensor,
                timestamp=current_time,
                temperature=round(random.uniform(15.0, 30.0), 2),
                humidity=round(random.uniform(40.0, 80.0), 2),
                wind_speed=round(random.uniform(0.0, 15.0), 2)
            )
            session.add(record)
            record_count += 1
        current_time += timedelta(minutes=30)

    session.commit()
    session.close()
    print(f"Inserted {record_count} sample records into the database.")


if __name__ == '__main__':
    seed_database()
