import logging

from dotenv import load_dotenv
from flask import Flask, redirect, request

try:
	from flask_migrate import Migrate
except ModuleNotFoundError:
	Migrate = None

from config import Config

from .models import db
from .routes import register_blueprints


migrate = Migrate() if Migrate is not None else None


def configure_logging(app):
	log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO

	if app.logger.handlers:
		for handler in app.logger.handlers:
			handler.setLevel(log_level)
			handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
	else:
		handler = logging.StreamHandler()
		handler.setLevel(log_level)
		handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
		app.logger.addHandler(handler)

	app.logger.setLevel(log_level)


def build_canonical_url(app):
	canonical_base_url = (app.config.get("CANONICAL_BASE_URL") or "").strip().rstrip("/")

	if canonical_base_url:
		canonical_url = f"{canonical_base_url}{request.path}"
	else:
		canonical_url = request.base_url

	if request.query_string:
		canonical_url = f"{canonical_url}?{request.query_string.decode('utf-8', errors='ignore')}"

	return canonical_url


def should_skip_canonical_redirect(app):
	if app.config.get("DEBUG"):
		return True

	current_host = (request.host or "").split(":", 1)[0].lower()
	return current_host in {"", "localhost", "127.0.0.1"}


def create_app():
	load_dotenv()

	flask_app = Flask(__name__)
	flask_app.config.from_object(Config)
	flask_app.secret_key = flask_app.config["SECRET_KEY"]

	db.init_app(flask_app)
	if migrate is not None:
		migrate.init_app(flask_app, db)
	configure_logging(flask_app)
	register_blueprints(flask_app)

	# Registrar la ruta de ads.txt
	from .ads_txt_route import ads_txt
	flask_app.add_url_rule('/ads.txt', view_func=ads_txt)

	@flask_app.context_processor
	def inject_canonical_url():
		return {"canonical_url": build_canonical_url(flask_app)}

	@flask_app.before_request
	def redirect_apex_to_www():
		if request.method not in {"GET", "HEAD"}:
			return None

		if should_skip_canonical_redirect(flask_app):
			return None

		if not flask_app.config.get("REDIRECT_APEX_TO_WWW", True):
			return None

		preferred_host = (flask_app.config.get("PREFERRED_HOST") or "").strip().lower()
		if not preferred_host:
			return None

		current_host = (request.host or "").split(":", 1)[0].lower()
		if current_host == preferred_host:
			return None

		apex_host = preferred_host[4:] if preferred_host.startswith("www.") else preferred_host
		if current_host != apex_host:
			return None

		return redirect(build_canonical_url(flask_app), code=301)

	return flask_app


app = create_app()
