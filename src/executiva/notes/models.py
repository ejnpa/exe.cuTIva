from sqlalchemy import Column,String, ForeignKey
from sqlalchemy.orm import relationship

from executiva.db.base import Base

class Notes(Base):
    __tablename__ = "notes"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True,nullable=False)
    school = Column(String, index=True, nullable= False)
    course = Column(String, index=True, nullable= False)
    year = Column(String, index=True, nullable= False)
    subject = Column(String, index=True, nullable= False)
    author = Column(String, index=True, nullable= False)
    file_url = Column(String, nullable= True)
    thumbnail_url = Column(String, nullable= True)
    inclusive_summary = Column(String, nullable= True)
    like_list = relationship(
        "NoteLike",
                back_populates="note",
                cascade="all, delete-orphan",
                passive_deletes=True
    )

class NoteLike(Base):
    __tablename__ = "note_like"
    user_id = Column(
        ForeignKey("users.id",ondelete="CASCADE"),
        primary_key=True
    )
    note_id = Column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True
    )
    note=relationship("Notes", back_populates="like_list")
