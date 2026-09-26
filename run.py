"""Entry point: `FLASK_CONFIG=development python run.py`.

Debug mode comes from the selected configuration, never from this file, so
running with the production configuration cannot expose Flask's interactive
debugger.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
