# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app/

# Install project using pyproject extras
RUN pip install --no-cache-dir -e .[youtube,ml,postgres] && pip install --no-cache-dir -e .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run uvicorn server when the container launches
# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app

# Run uvicorn server when the container launches
CMD ["uvicorn", "src.youtube_extension.main:app", "--host", "0.0.0.0", "--port", "8080"]
