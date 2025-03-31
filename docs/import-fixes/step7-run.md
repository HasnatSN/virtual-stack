# Step 7: Run with Correct PYTHONPATH

## Running the Application

After fixing all import issues, it's time to run the application with the correct PYTHONPATH setting.

## Option 1: Running from the src directory

This is the simplest approach:

```bash
cd src
python3 -m uvicorn virtualstack.main:app
```

## Option 2: Running from the project root

If you need to run from the project root, use:

```bash
PYTHONPATH=$PYTHONPATH:$(pwd)/src python3 -m uvicorn virtualstack.main:app
```

## Option 3: Running with additional command-line options

If you need to specify additional options like port or reload:

```bash
cd src
python3 -m uvicorn virtualstack.main:app --reload --host 0.0.0.0 --port 8000
```

## Verifying the API is working

Once the application is running, test that it's working by making a request to the health endpoint:

```bash
curl http://localhost:8000/health
```

You should get a response similar to:

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

To access the API documentation, open:

```
http://localhost:8000/docs
```

This should display the Swagger UI with all the available endpoints. 