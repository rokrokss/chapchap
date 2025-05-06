dev:
	APP_ENV=development LOG_JSON_FORMAT=false poetry run fastapi dev main.py

prod:
	APP_ENV=production LOG_JSON_FORMAT=true uvicorn main:app --host 0.0.0.0 --log-config uvicorn_disable_logging.json
