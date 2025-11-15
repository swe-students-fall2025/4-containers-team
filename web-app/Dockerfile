FROM python:3.10-slim

# Set working directory
WORKDIR /web-app

# Install pipenv
RUN pip install pipenv

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install

# Copy application code
COPY . .

# Set environment variables
ENV 

# Expose port
EXPOSE 8000

# Run the application
CMD ["pipenv", "run", "python", "app.py"]

