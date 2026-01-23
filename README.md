# Beginner to Ninja Backend Projects Using Django

This repository contains a collection of beginner to advanced backend projects developed using Django, based on the project ideas from [Roadmap.sh](https://roadmap.sh/backend/project-ideas). The purpose of this repository is to practice and enhance backend development skills by building real-world projects, focusing on a range of topics that are crucial for mastering backend development.

## Purpose

The primary goal of this repository is to provide a structured way for developers to practice and improve their backend development skills by building advanced projects. Each project covers important concepts such as:

- API Development
- Authentication and Authorization
- Database Design and Optimization
- Asynchronous Processing
- Caching and Performance Tuning
- Microservices Architecture
- WebSocket Implementation

These projects are built using **Django**, a powerful web framework for building scalable, maintainable, and efficient backend systems. By following the project ideas from Roadmap.sh, developers can challenge themselves with real-world problems and sharpen their skills in various aspects of backend development.

## Projects Covered

The repository aims to implement the following backend projects inspired by [Roadmap.sh](https://roadmap.sh/backend/project-ideas):

1. **URL Shortener**: A system to shorten long URLs, with custom aliases and analytics tracking.
2. **File Sharing Service**: A secure service that allows users to upload, share, and manage files.
3. **Authentication System**: A robust system that handles user registration, login, and session management with JWT.
4. **Social Media Platform**: A basic version of a social media site where users can post, comment, and interact.
5. **Chat Application**: A real-time chat application using Django Channels and WebSockets.
6. **Task Queue System**: A system for background job processing, using Django and a task queue like Celery.
7. **Blog Platform**: A multi-user blogging platform with advanced features like content management, tagging, and commenting.
8. **E-Commerce System**: A fully functional e-commerce site with user authentication, product management, and payment integration.

... and more!

## Technologies Used

The projects are primarily built using:

- **Django**: A high-level Python web framework that encourages rapid development and clean, pragmatic design.
- **PostgreSQL**: The primary database used for storing and managing project data.
- **Docker**: For containerization, allowing easy setup and deployment of each project.
- **Redis**: For caching and handling asynchronous tasks (used in specific projects).

## How to Use

1. Clone the repository:
   ```bash
   git clone https://github.com/AgPriyanshu/backend-projects.git
   ```
2. Navigate to the project folder and follow the specific setup instructions for each project, which are included in the respective directories.

3. Run the projects locally using:
   ```bash
   python manage.py runserver
   ```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests to improve the projects or add new ones.

## Docker Image Optimization

This project uses [SlimToolkit](https://github.com/slimtoolkit/slim) to automatically optimize Docker images in the CI/CD pipeline, reducing image sizes by up to 90% while maintaining full functionality.

### Automated Optimization (CI/CD)

When you push to the `master` branch, GitHub Actions automatically:

1. Builds the Docker image
2. Optimizes it with SlimToolkit
3. Pushes the optimized image to GitHub Container Registry
4. Reports size reduction in the workflow summary

### Local Optimization

To optimize images locally:

#### Install SlimToolkit

**macOS:**

```bash
brew install slimtoolkit/tap/slim
```

**Linux:**

```bash
curl -L -o slim.tar.gz https://github.com/slimtoolkit/slim/releases/download/1.40.11/dist_linux.tar.gz
tar -xvf slim.tar.gz
sudo mv dist_linux/slim /usr/local/bin/
sudo mv dist_linux/slim-sensor /usr/local/bin/
```

#### Build and Optimize

```bash
# Build the original image
docker build -t backend-projects:original .

# Optimize with SlimToolkit
slim build \
  --target backend-projects:original \
  --tag backend-projects:slim \
  --http-probe=true \
  --http-probe-cmd='http://localhost:8000/health/' \
  --continue-after=60

# Compare sizes
docker images | grep backend-projects
```

#### Run Optimized Image

```bash
docker run -p 8000:8000 --env-file .env backend-projects:slim
```

### Configuration

SlimToolkit settings are defined in `.slimtoolkit.yaml`. The configuration includes:

- HTTP probes to test Django endpoints during optimization
- Path preservation for required files and directories
- Environment variable preservation
- Exclusion patterns for unnecessary files

## License

This repository is licensed under the MIT License.
