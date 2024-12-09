from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class Pet(Base):
    __tablename__ = "pets"
    id = Column(String(20), primary_key=True)
    name = Column(String(100))
    animal_type = Column(String(20))
    created = Column(DateTime())

    def update(self, id=None, name=None, animal_type=None, tags=None, created=None):
        if name is not None:
            self.name = name
        if animal_type is not None:
            self.animal_type = animal_type
        if created is not None:
            self.created = created

    def dump(self):
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}


def init_db():
    """
    Initialize the database and return a sessionmaker object.
    `check_same_thread` and `StaticPool` are helpful for unit testing of
    in-memory sqlite databases; they should not be used in production.
    https://stackoverflow.com/questions/6519546/scoped-sessionsessionmaker-or-plain-sessionmaker-in-sqlalchemy
    """
    engine = create_engine(
        url="sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
