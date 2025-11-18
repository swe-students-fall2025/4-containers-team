FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install pipenv
RUN pip install pipenv

# Copy dependency files first (for better caching)
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install --dev

# Install whisper from git
RUN pipenv run pip install git+https://github.com/openai/whisper.git

# Copy application code
COPY . .

# Run the application
CMD ["pipenv", "run", "python", "main.py"]

