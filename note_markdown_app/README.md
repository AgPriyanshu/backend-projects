# Markdown Note-taking App

A web application built using Django to provide a REST API for uploading, processing, and managing Markdown-based notes. The app also includes features for grammar checking and rendering Markdown text into HTML.

---

## Features

1. **Markdown Note Management**:

   - Upload Markdown notes through RESTful APIs.
   - Store and manage Markdown files while avoiding name collisions.

2. **Grammar Checking**:

   - Provides an endpoint to check the grammar of notes.

3. **Markdown Rendering**:
   - Convert and return Markdown notes as rendered HTML.

---

## Technologies Used

- **Framework**: Django
- **Libraries**:
  - `markdown`: For rendering Markdown into HTML.
  - `django-rest-framework (DRF)`: For building the REST APIs.
  - `grammar-check` (or any grammar-checking library): For grammar validation.
- **Persistent Storage**: SQLite (or any database of your choice).

## DB

[Schema](https://dbdiagram.io/d/Backend-Projects-67135d4e97a66db9a387e059)

<iframe width="560" height="315" src='https://dbdiagram.io/e/67135d4e97a66db9a387e059/67135e9497a66db9a387f35e'> </iframe>
