from app.models import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database schema initialized.")


if __name__ == "__main__":
    init_db()
