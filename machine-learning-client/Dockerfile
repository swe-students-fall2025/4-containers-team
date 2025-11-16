FROM python:3.10-slim

#for whisper (stt model)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists*

# Set working directory
WORKDIR /app
COPY . .

# Install pipenv
RUN pip install pipenv \
&& pipenv install --deploy --ignore-pipfile \
 && pipenv run pip install openai-whisper

COPY . .
# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install

# Copy application code
COPY . .

# Set environment variables
ENV 

# Run the application
CMD ["pipenv", "run", "python", "app.py"]

