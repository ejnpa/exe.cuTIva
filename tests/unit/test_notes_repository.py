import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from executiva.db.base import Base
from executiva.notes.models import NoteLike, Notes
from executiva.notes.repository import NotesRepository
from executiva.users.models import User


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    session.add(User(id=1, username="Ana", email="ana@example.pt", password="hash"))
    session.add(User(id=2, username="Rui", email="rui@example.pt", password="hash"))
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def make_note(note_id="nota-1", author="ana@example.pt", **changes):
    values = {
        "id": note_id,
        "title": "Apontamentos de teste",
        "school": "Escola A",
        "course": "Curso A",
        "year": "1",
        "subject": "Programação",
        "author": author,
        "file_url": "https://storage.test/documento.pdf",
        "thumbnail_url": "https://storage.test/thumb_documento.png",
    }
    values.update(changes)
    return Notes(**values)


def test_create_and_get_note(db_session):
    repository = NotesRepository(db_session)

    created = repository.create({
        "id": "nota-1",
        "title": "Introdução",
        "school": "Escola A",
        "course": "Curso A",
        "year": "1",
        "subject": "Programação",
        "author": "ana@example.pt",
        "file_url": "/documento.pdf",
        "thumbnail_url": None,
    })

    assert created.id == "nota-1"
    assert repository.get_by_id("nota-1").title == "Introdução"
    assert repository.get_by_id("ausente") is None


def test_delete_note_removes_existing_note_and_ignores_missing_id(db_session):
    repository = NotesRepository(db_session)
    repository.create({
        "id": "nota-1",
        "title": "Introdução",
        "school": "Escola A",
        "course": "Curso A",
        "year": "1",
        "subject": "Programação",
        "author": "ana@example.pt",
        "file_url": "/documento.pdf",
    })

    repository.delete_note("nota-1")
    repository.delete_note("ausente")

    assert repository.get_by_id("nota-1") is None


def test_get_by_author_apenas_devolve_notas_do_autor(db_session):
    db_session.add_all([
        make_note("nota-1", "ana@example.pt"),
        make_note("nota-2", "rui@example.pt"),
    ])
    db_session.commit()
    repository = NotesRepository(db_session)

    result = repository.get_by_author("ana@example.pt", current_user_id=1)

    assert [item["id"] for item in result] == ["nota-1"]
    assert result[0]["file_url"] == "/api/notes/nota-1/view"
    assert result[0]["thumbnail_url"] == "/api/notes/nota-1/thumbnail"
    assert result[0]["likes"] == 0
    assert result[0]["liked_by_user"] is False


def test_get_all_with_filters_aplica_filtros_e_valores_todos(db_session):
    db_session.add_all([
        make_note("nota-1", school="Escola A", course="Curso A", year="1", subject="Programação"),
        make_note("nota-2", school="Escola B", course="Curso B", year="2", subject="Matemática"),
    ])
    db_session.commit()
    repository = NotesRepository(db_session)

    filtered = repository.get_all_with_filters(school="Escola A")
    all_notes = repository.get_all_with_filters(
        school="Todas",
        course="Todos",
        year="Todos",
        subject="Todas",
    )

    assert [note["id"] for note in filtered] == ["nota-1"]
    assert {note["id"] for note in all_notes} == {"nota-1", "nota-2"}


def test_format_notes_indica_gostos_e_url_de_miniatura_ausente(db_session):
    note = make_note("nota-1", thumbnail_url=None)
    note.like_list.append(NoteLike(user_id=1, note_id="nota-1"))
    db_session.add(note)
    db_session.commit()
    repository = NotesRepository(db_session)

    for_user = repository.get_all_with_filters(current_user_id=1)[0]
    other_user = repository.get_all_with_filters(current_user_id=2)[0]

    assert for_user["likes"] == 1
    assert for_user["liked_by_user"] is True
    assert other_user["liked_by_user"] is False
    assert for_user["thumbnail_url"] is None


def test_add_like_e_remove_like_sao_idempotentes(db_session):
    note = make_note()
    db_session.add(note)
    db_session.commit()
    repository = NotesRepository(db_session)

    repository.add_like("nota-1", 1)
    repository.add_like("nota-1", 1)
    assert repository.count_likes("nota-1") == 1

    repository.remove_like("nota-1", 1)
    repository.remove_like("nota-1", 1)
    assert repository.count_likes("nota-1") == 0


def test_count_likes_devolve_zero_sem_registos(db_session):
    repository = NotesRepository(db_session)

    assert repository.count_likes("nota-inexistente") == 0
