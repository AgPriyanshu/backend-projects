# Blogs API

This is a simple Django REST API backend that allows performing basic CRUD (Create, Read, Update, Delete) operations on todo tasks.

## Endpoints

- **GET** `/` - Fetch all tasks
- **POST** `/` - Add a new task
- **PATCH** `/{id}/` - Update an existing task
- **DELETE** `/{id}/` - Delete a task

## Instructions

### Local Setup

1. **Install dependencies**:
   
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations**:
   
   ```bash
   python manage.py migrate
   ```
3. **Run the server locally**:
   
   ```bash
   python manage.py run server
   ```
   The API will be available at http://127.0.0.1:8000/.
  
### Running Tests

To run the test suite, use the following command:
```bash
python manage.py tests
```