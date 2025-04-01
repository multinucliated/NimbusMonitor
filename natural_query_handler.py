from datetime import datetime

from openai import OpenAI
from pydantic import BaseModel, Field
import os

# Initialize the OpenAI client.
api_key = os.environ.get("OPENAI_API_KEY", None)
if api_key is None:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)


# Pydantic model for natural language query input.
class NLQuery(BaseModel):
    input_query: str


# Pydantic model for the SQL query output.
class SQLQuery(BaseModel):
    query: str = Field(title="query",
                       description="This will hold the valid SQL query "
                                   "or else it will be empty string.")
    valid_query: bool = Field(title="valid_query",
                              description="This field indicates whether the "
                                          "SQL query is valid or not. "
                                          "Moreover if its not adhering to "
                                          "the things which is asked in the "
                                          "prompt, it will be returned as "
                                          "false or else if the sql query is "
                                          "valid and adhering to the prompt, "
                                          "it will be returned as true.")


def parse_nl_query(nl_query: str) -> SQLQuery:
    # Provide detailed database schema context.

    db_context = """
                    Database Schema:
                    Table: sensor_metrics
                    Columns:
                      - id (INTEGER, primary key)
                      - sensor_id (INTEGER) -- sensor identifier
                      - timestamp (DATETIME) -- reading timestamp
                      - temperature (FLOAT) -- temperature in degrees Celsius
                      - humidity (FLOAT) -- humidity percentage
                      - wind_speed (FLOAT) -- wind speed in km/h
                    """

    prompt = f""" You are an expert SQL developer. Given the following 
    natural language query and the provided database schema, generate a valid 
    SQLite query that can be executed on the database. 
    
    ALLOWED SQL Aggregate Functions:
    -  min
    -  max
    -  sum
    -  average

    {db_context}
    
    Current Timezone: UTC
    Current Date and Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
    
    Natural Language Query:
    "{nl_query}"
    """

    # Call the OpenAI model with the improved prompt.
    response = client.beta.chat.completions.parse(
        model="gpt-4o",  # Adjust the model name if needed.
        temperature=0,
        messages=[
            {"role": "system",
             "content": prompt
             }
        ],
        response_format=SQLQuery,
    )
    # Extract the SQL query from the response.
    text = response.choices[0].message
    return text.parsed


# Example usage:
if __name__ == "__main__":
    nl_input = ("What was the average temperature and humidity from sensor "
                "1 and 2 between 2025-01-01 and 2025-01-31?")
    sql_result = parse_nl_query(nl_input)
    print(sql_result)
