try:
    from .api import app
except ImportError:
    from api import app


if __name__ == "__main__":
    app.run()
