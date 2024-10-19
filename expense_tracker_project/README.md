# Expense Tracker API

This is a simple Django REST API backend that allows CRUD operations for Expense tracking data.

### Database Schema 

[Expense Tracker ERD](https://dbdocs.io/priyanshu81212/Expense-Tracker-ERD?view=relationships)

<iframe width="560" height="315" src='https://dbdiagram.io/e/67135d4e97a66db9a387e059/67135e9497a66db9a387f35e'> </iframe>

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