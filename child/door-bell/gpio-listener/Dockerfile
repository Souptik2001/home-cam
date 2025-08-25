# Use a Python base image that is compatible with Raspberry Pi's ARM architecture
FROM python:3.9-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# This is done in a separate step to leverage Docker's layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual script into the container
COPY door-bell-listener.py .

# Command to run when the container starts
CMD ["python", "door-bell-listener.py"]