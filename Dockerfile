# Use the official Python 3.11.7 slim-buster image.
FROM python:3.11.7

# Set the working directory to the same directory as the Dockerfile.
WORKDIR /app

# Copy the requirements file into the container.
COPY requirements.txt .

# Create and activate the virtual environment.
RUN python -m venv llama_deidentification && \
    /app/llama_deidentification/bin/pip install --no-cache-dir -r requirements.txt
    # source llama_deidentification/bin/activate && \
    # pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container.
COPY . .

# Expose the port your application listens on
EXPOSE 3000

# Specify the command to run your application.
CMD ["/app/llama_deidentification/bin/python", "llama_server.py"]