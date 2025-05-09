# PDFMerger

A web application to securely merge PDF files locally without using third-party websites or applications.

## Features

- Upload and merge multiple PDF files
- Process PDFs entirely in memory for enhanced security
- Secure downloads with expiring links (24 hours by default)
- No third-party services or data sharing
- Simple, intuitive user interface
- Memory-efficient processing for large documents

## Getting Started with Docker

The easiest way to run PDF Merger is using Docker and Docker Compose.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Running with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PDFMerger.git
   cd PDFMerger
2. Run the application using Docker Compose:
```docker-compose up -d ```
3. Access the application in your browser:
```http://localhost:5000 ```
4. To stop the application:
``` docker-compose down ```
5. Running with Docker (without Compose)
If you prefer to use Docker directly:
``` # Build the Docker image
docker build -t pdf-merger .

# Run the container
docker run -p 5000:5000 -v pdf_data:/app/data pdf-merger
```
