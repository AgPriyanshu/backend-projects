# Agent Instructions

This document provides guidelines for AI agents working on this codebase.

## General Guidelines

- Every comment should end with a full stop.
- Do not add unnecessary comments.
- Use code block division with a blank line for best readability.
- Add a blank line before each `if` or `for` loop for readability.
- Do not create tests, examples, or run scripts without asking the user first.

## Technology Stack

- This repository uses **Django** as the web framework.
- This repository includes **Kubernetes (k8s)** configurations for deploying the application.

## Project Structure

### Shared App

The `shared` app is used for:

- Endpoints that are common across the entire project.
- All shared utility functions and modules.

## Endpoint Development

When creating a new endpoint or updating an existing endpoint:

- Automatically update the relevant documentation.
- Automatically update or create corresponding tests.

## Running Django Commands

- Always use **Docker Compose** to run any Django-related commands.
- Examples:
  - Migrations: `docker compose exec web python manage.py migrate`
  - Make migrations: `docker compose exec web python manage.py makemigrations`
  - Shell: `docker compose exec web python manage.py shell`

## Python Package Management

- **Do not use local Python** for package management.
- To add a new pip package:
  1. Install the package inside the Docker Compose container: `docker compose exec web pip install <package-name>`
  2. Check the installed version: `docker compose exec web pip show <package-name>`
  3. Update `requirements.txt` with the exact version installed in the container.
