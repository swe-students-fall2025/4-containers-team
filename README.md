![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)  
[![ml-client-ci](https://github.com/swe-students-fall2025/4-containers-team/actions/workflows/ml-client-ci.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/4-containers-team/actions/workflows/ml-client-ci.yml)  
[![web-app-ci](https://github.com/swe-students-fall2025/4-containers-team/actions/workflows/web-app-ci.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/4-containers-team/actions/workflows/web-app-ci.yml)

# Containerized App Exercise

## Project Overview

**World Tour by Ear** is a machine learning application that detects and identifies spoken languages from audio recordings. Users can record 10 seconds of themselves speaking, and the system will analyze the audio to predict which language they're speaking.

### Key Features

-   **Audio Recording**: Web interface for recording 10-second audio clips
-   **Language Detection**: Machine learning-powered language identification from audio
-   **Result Dashboard**: Visual display of language detection results and statistics

## Team Members

-   [Catherine Yu](https://github.com/catherineyu2014)
-   [Evelynn Mak](https://github.com/evemak)
-   [Kevin Pham](https://github.com/knp4830)
-   [Connor Lee](https://github.com/Connorlee487)
-   [Jubilee Tang](https://github.com/MajesticSeagull26)

## Prerequisites

Before running this project, ensure you have the following installed:

-   [Docker](https://docs.docker.com/get-docker/)
-   [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

1. **Clone the repository:**

    ```bash
    git clone https://github.com/swe-students-fall2025/4-containers-team.git
    cd 4-containers-team
    ```

2. **Start all services with Docker Compose:**

    ```bash
    docker-compose up --build
    ```

3. **Access the application:**

    - Web application: http://localhost:8000
    - MongoDB: localhost:27017

4. **Stop all services:**
    ```bash
    docker-compose down
    ```

## Configuration

### Environment Variables

The application uses environment variables configured in `docker-compose.yml`. The following variables are set:

**Machine Learning Client:**

-   `MONGO_URI`: (Optional) Full MongoDB connection URI. If not set, connection is built from `MONGODB_HOST` and `MONGODB_PORT`
-   `MONGODB_HOST`: MongoDB service name (default: `mongodb`)
-   `MONGODB_PORT`: MongoDB port (default: `27017`)
-   `MONGODB_DATABASE`: Database name (default: `proj4`)
-   `COLLECTION_INTERVAL`: How often to process data in seconds (default: `60`)

**Web Application:**

-   `MONGO_URI`: (Optional) Full MongoDB connection URI. If not set, connection is built from `MONGODB_HOST` and `MONGODB_PORT`
-   `MONGODB_HOST`: MongoDB service name (default: `mongodb`)
-   `MONGODB_PORT`: MongoDB port (default: `27017`)
-   `MONGODB_DATABASE`: Database name (default: `proj4`)
-   `PORT`: Flask application port (default: `5000`)

**MongoDB:**

-   `MONGO_INITDB_DATABASE`: Initial database name (default: `proj4`)

### Optional Configuration File

If you need to use a custom MongoDB connection string (e.g., for external MongoDB or authentication), you can create a `.env` file in the root directory. See `.env.example` for a template.

**To use a custom MongoDB URI:**

1. Copy the example file:

    ```bash
    cp .env.example .env
    ```

2. Edit `.env` and set your `MONGO_URI`:

    ```bash
    MONGO_URI=mongodb://username:password@host:port/
    ```

3. Docker Compose will automatically read the `.env` file when you run `docker-compose up`.

**Note:** The `.env` file is optional. If not provided, the application will use the default connection built from `MONGODB_HOST` and `MONGODB_PORT` as configured in `docker-compose.yml`.
