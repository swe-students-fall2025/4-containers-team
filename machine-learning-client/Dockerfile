FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
COPY . .

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install pipenv
RUN pip install pipenv
RUN pipenv install --deploy --ignore-pipfile

RUN pipenv run pip install git+https://github.com/openai/whisper.git

# Install dependencies
RUN pipenv install

# Copy application code
COPY . .

# Set environment variables


# Run the application
CMD ["pipenv", "run", "python", "main.py"]

