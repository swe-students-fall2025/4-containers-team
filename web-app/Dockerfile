FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install pipenv
RUN pip install pipenv

# Copy dependency files first (for caching)
COPY Pipfile Pipfile.lock ./

# Install dependencies system-wide inside Docker virtual env
RUN pipenv install

# Copy the rest of your app
COPY . .

# Expose port Flask listens on
EXPOSE 5000

# Run the Flask app
CMD ["pipenv", "run", "python", "app.py"]
