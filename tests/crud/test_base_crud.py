"""
Direct unit tests for BaseCRUD (apps/CRUD/base.py).

Unlike the rest of the test suite (which drives everything through HTTP
endpoints), these tests call BaseCRUD methods directly against `db_session`.
That's on purpose: several BaseCRUD branches (get_or_create, exists,
commit=False, dict-based input, filters passed as a dict, forced DB errors)
are never reached through any endpoint, because RouterFactory only ever
calls a subset of BaseCRUD's public API in a specific way.
"""

from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.from_models.item import item_crud
from apps.CRUD.from_models.task import sub_task_crud, task_crud
from apps.CRUD.from_models.user import user_crud
from apps.models.item import ItemType
from apps.schemas.item import ItemCreate
from apps.schemas.user import UserCreate


async def _make_user(db_session: AsyncSession, email: str = "crud@example.com"):
    return await user_crud.create(
        db_session, UserCreate(email=email, password="password123", name="CRUD User")
    )


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


async def test_create_accepts_plain_dict(db_session: AsyncSession):
    item = await item_crud.create(
        db_session, {"name": "Dict Item", "item_type": ItemType.WEAPON}
    )
    assert item.id is not None
    assert item.name == "Dict Item"


async def test_create_commit_false_only_flushes(db_session: AsyncSession):
    item_in = ItemCreate(name="Flushed Item", item_type=ItemType.WEAPON)
    item = await item_crud.create(db_session, item_in, commit=False)

    # flush() assigns a PK and makes the row visible within the transaction...
    assert item.id is not None
    assert await item_crud.count(db_session) == 1

    # ...but it was never committed, so a rollback discards it entirely.
    await db_session.rollback()
    assert await item_crud.count(db_session) == 0


async def test_create_integrity_error_on_missing_required_field(
    db_session: AsyncSession,
):
    # item_type is NOT NULL at the DB level; bypassing the Pydantic schema
    # via a raw dict lets a genuine IntegrityError reach BaseCRUD.
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.create(db_session, {"name": "No Type"})
    assert exc_info.value.status_code == 400
    assert "integrity" in exc_info.value.detail.lower()


async def test_create_integrity_error_on_duplicate_unique_field(
    db_session: AsyncSession,
):
    await _make_user(db_session, email="dup@example.com")
    with pytest.raises(HTTPException) as exc_info:
        await _make_user(db_session, email="dup@example.com")
    assert exc_info.value.status_code == 400


async def test_create_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    async def broken_commit():
        raise SQLAlchemyError("connection lost")

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.create(
            db_session, ItemCreate(name="X", item_type=ItemType.WEAPON)
        )
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


async def test_get_returns_none_when_not_found_and_not_raising(
    db_session: AsyncSession,
):
    assert await item_crud.get(db_session, 999_999) is None


async def test_get_raise_not_found_raises_404(db_session: AsyncSession):
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get(db_session, 999_999, raise_not_found=True)
    assert exc_info.value.status_code == 404


async def test_get_loads_nested_dot_relationships(db_session: AsyncSession):
    user = await _make_user(db_session)
    task = await task_crud.create(db_session, {"name": "T1", "user_id": user.id})
    await sub_task_crud.create(db_session, {"name": "ST1", "task_id": task.id})

    fetched = await user_crud.get(
        db_session, user.id, relationships=["tasks.sub_tasks"]
    )

    assert fetched is not None
    assert fetched.tasks[0].sub_tasks[0].name == "ST1"


async def test_get_relationship_resolves_leading_underscore_fallback(
    db_session: AsyncSession,
):
    # `inventory_items` is a @property; the real relationship is
    # `_inventory_items`. _get_rel_attr() should fall back to it.
    user = await _make_user(db_session)
    item = await item_crud.create(
        db_session, ItemCreate(name="Potion", item_type=ItemType.CONSUMABLE)
    )
    await user_crud.add_to_inventory(db_session, user.id, item.id)

    fetched = await user_crud.get(
        db_session, user.id, relationships=["inventory_items"]
    )

    assert fetched is not None
    assert len(fetched._inventory_items) == 1


async def test_get_with_bogus_relationship_name_surfaces_as_500(
    db_session: AsyncSession,
):
    # "name" exists on the model but isn't a relationship, so selectinload()
    # blows up at execute() time with a SQLAlchemyError subclass.
    item = await item_crud.create(
        db_session, ItemCreate(name="Bad Rel", item_type=ItemType.WEAPON)
    )
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get(db_session, item.id, relationships=["name"])
    assert exc_info.value.status_code == 500


async def test_get_ignores_relationship_name_that_does_not_exist(
    db_session: AsyncSession,
):
    item = await item_crud.create(
        db_session, ItemCreate(name="Ignore Me", item_type=ItemType.WEAPON)
    )
    fetched = await item_crud.get(
        db_session, item.id, relationships=["totally_made_up_field"]
    )
    assert fetched is not None


# ---------------------------------------------------------------------------
# get_multi()
# ---------------------------------------------------------------------------


async def test_get_multi_filters_by_exact_value_and_list(db_session: AsyncSession):
    await item_crud.create(db_session, ItemCreate(name="W1", item_type=ItemType.WEAPON))
    await item_crud.create(db_session, ItemCreate(name="A1", item_type=ItemType.ARMOR))
    await item_crud.create(db_session, ItemCreate(name="A2", item_type=ItemType.ARMOR))

    weapons = await item_crud.get_multi(
        db_session, filters={"item_type": ItemType.WEAPON}
    )
    assert len(weapons) == 1

    weapons_and_armor = await item_crud.get_multi(
        db_session, filters={"item_type": [ItemType.WEAPON, ItemType.ARMOR]}
    )
    assert len(weapons_and_armor) == 3


async def test_get_multi_loads_nested_dot_relationships(db_session: AsyncSession):
    user = await _make_user(db_session)
    task = await task_crud.create(db_session, {"name": "T1", "user_id": user.id})
    await sub_task_crud.create(db_session, {"name": "ST1", "task_id": task.id})

    users = await user_crud.get_multi(db_session, relationships=["tasks.sub_tasks"])

    assert users[0].tasks[0].sub_tasks[0].name == "ST1"


async def test_get_multi_loads_single_level_relationship(db_session: AsyncSession):
    user = await _make_user(db_session)
    await task_crud.create(db_session, {"name": "T1", "user_id": user.id})

    tasks = await task_crud.get_multi(db_session, relationships=["user"])

    assert tasks[0].user.id == user.id


async def test_get_with_broken_nested_relationship_surfaces_as_500(
    db_session: AsyncSession,
):
    # Second level of the dotted path ("bogus") isn't a relationship on
    # ShopItem, so the code falls back to passing a raw string to
    # selectinload(), which SQLAlchemy itself rejects.
    item = await item_crud.create(
        db_session, ItemCreate(name="Deep Rel", item_type=ItemType.WEAPON)
    )
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get(db_session, item.id, relationships=["shop_items.bogus"])
    assert exc_info.value.status_code == 500


async def test_get_multi_with_bogus_relationship_name_surfaces_as_500(
    db_session: AsyncSession,
):
    # "name" exists on the model but isn't a relationship, hitting the
    # fallback branch that tries selectinload() on it anyway.
    await item_crud.create(
        db_session, ItemCreate(name="Bad Rel List", item_type=ItemType.WEAPON)
    )
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get_multi(db_session, relationships=["name"])
    assert exc_info.value.status_code == 500


async def test_get_multi_ignores_relationship_name_that_does_not_exist(
    db_session: AsyncSession,
):
    await item_crud.create(
        db_session, ItemCreate(name="Ignore Me Too", item_type=ItemType.WEAPON)
    )
    items = await item_crud.get_multi(
        db_session, relationships=["totally_made_up_field"]
    )
    assert len(items) == 1


async def test_get_multi_with_broken_nested_relationship_surfaces_as_500(
    db_session: AsyncSession,
):
    await item_crud.create(
        db_session, ItemCreate(name="Deep Rel List", item_type=ItemType.WEAPON)
    )
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get_multi(db_session, relationships=["shop_items.bogus"])
    assert exc_info.value.status_code == 500


async def test_get_multi_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    async def broken_execute(*args, **kwargs):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db_session, "execute", broken_execute)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get_multi(db_session)
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


async def test_update_commit_false_is_discarded_on_rollback(db_session: AsyncSession):
    item = await item_crud.create(
        db_session, ItemCreate(name="Orig", item_type=ItemType.WEAPON)
    )
    item_id = item.id
    updated = await item_crud.update(
        db_session, id=item_id, obj_in={"name": "Changed"}, commit=False
    )
    assert updated is not None
    assert updated.name == "Changed"

    # rollback() expires all attributes on tracked instances, including the
    # PK, so we must have captured item_id beforehand.
    await db_session.rollback()
    reverted = await item_crud.get(db_session, item_id)
    assert reverted is not None
    assert reverted.name == "Orig"


async def test_update_integrity_error_on_duplicate_unique_field(
    db_session: AsyncSession,
):
    await _make_user(db_session, email="a@example.com")
    u2 = await _make_user(db_session, email="b@example.com")

    with pytest.raises(HTTPException) as exc_info:
        await user_crud.update(db_session, id=u2.id, obj_in={"email": "a@example.com"})
    assert exc_info.value.status_code == 400


async def test_update_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    item = await item_crud.create(
        db_session, ItemCreate(name="Orig", item_type=ItemType.WEAPON)
    )

    async def broken_commit():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.update(db_session, id=item.id, obj_in={"name": "New"})
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


async def test_delete_commit_false_is_undone_on_rollback(db_session: AsyncSession):
    item = await item_crud.create(
        db_session, ItemCreate(name="ToDelete", item_type=ItemType.WEAPON)
    )
    item_id = item.id
    await item_crud.delete(db_session, id=item_id, commit=False)

    # rollback() expires all attributes on tracked instances, including the
    # PK, so we must have captured item_id beforehand.
    await db_session.rollback()
    still_there = await item_crud.get(db_session, item_id)
    assert still_there is not None


async def test_delete_integrity_error_returns_400(
    db_session: AsyncSession, monkeypatch
):
    item = await item_crud.create(
        db_session, ItemCreate(name="Protected", item_type=ItemType.WEAPON)
    )

    async def broken_commit():
        raise IntegrityError("DELETE ...", {}, Exception("FK violation"))

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.delete(db_session, id=item.id)
    assert exc_info.value.status_code == 400
    assert "referenced" in exc_info.value.detail.lower()


async def test_delete_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    item = await item_crud.create(
        db_session, ItemCreate(name="Doomed", item_type=ItemType.WEAPON)
    )

    async def broken_commit():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.delete(db_session, id=item.id)
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# exists()
# ---------------------------------------------------------------------------


async def test_exists_true_and_false(db_session: AsyncSession):
    item = await item_crud.create(
        db_session, ItemCreate(name="Exists", item_type=ItemType.WEAPON)
    )
    assert await item_crud.exists(db_session, item.id) is True
    assert await item_crud.exists(db_session, 999_999) is False


async def test_exists_swallows_db_error_and_returns_false(
    db_session: AsyncSession, monkeypatch
):
    # get() already converts SQLAlchemyError into an HTTPException, so the
    # `except SQLAlchemyError` in exists() can only ever fire if something
    # bypasses get()'s own error handling entirely - simulated here by
    # patching get() itself.
    async def broken_get(*args, **kwargs):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(item_crud, "get", broken_get)
    assert await item_crud.exists(db_session, 1) is False


# ---------------------------------------------------------------------------
# count()
# ---------------------------------------------------------------------------


async def test_count_with_filters_and_search_fields(db_session: AsyncSession):
    await item_crud.create(
        db_session, ItemCreate(name="Sword of Doom", item_type=ItemType.WEAPON)
    )
    await item_crud.create(
        db_session, ItemCreate(name="Shield", item_type=ItemType.ARMOR)
    )

    assert (
        await item_crud.count(db_session, filters={"item_type": ItemType.WEAPON}) == 1
    )
    assert (
        await item_crud.count(
            db_session, filters={"item_type": [ItemType.WEAPON, ItemType.ARMOR]}
        )
        == 2
    )
    assert await item_crud.count(db_session, search_fields={"name": "sword"}) == 1


async def test_count_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    async def broken_execute(*args, **kwargs):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db_session, "execute", broken_execute)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.count(db_session)
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# get_or_create()
# ---------------------------------------------------------------------------


async def test_get_or_create_creates_then_returns_existing(db_session: AsyncSession):
    item1, created1 = await item_crud.get_or_create(
        db_session, name="Unique Sword", defaults={"item_type": ItemType.WEAPON}
    )
    assert created1 is True

    item2, created2 = await item_crud.get_or_create(
        db_session, name="Unique Sword", defaults={"item_type": ItemType.ARMOR}
    )
    assert created2 is False
    assert item2.id == item1.id
    # defaults are only applied on creation, not when an existing row is found
    assert item2.item_type == ItemType.WEAPON


async def test_get_or_create_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    async def broken_execute(*args, **kwargs):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db_session, "execute", broken_execute)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.get_or_create(db_session, name="X")
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# bulk_create()
# ---------------------------------------------------------------------------


async def test_bulk_create_commit_false_is_discarded_on_rollback(
    db_session: AsyncSession,
):
    items_in: list[ItemCreate | dict[str, Any]] = [
        ItemCreate(name="B1", item_type=ItemType.WEAPON),
        ItemCreate(name="B2", item_type=ItemType.ARMOR),
    ]
    created = await item_crud.bulk_create(db_session, items_in, commit=False)
    assert len(created) == 2

    await db_session.rollback()
    assert await item_crud.count(db_session) == 0


async def test_bulk_create_with_relationships_eager_loads_them(
    db_session: AsyncSession,
):
    user = await _make_user(db_session)
    tasks_in = [
        {"name": "BT1", "user_id": user.id},
        {"name": "BT2", "user_id": user.id},
    ]
    created = await task_crud.bulk_create(db_session, tasks_in, relationships=["user"])
    assert all(t.user.id == user.id for t in created)


async def test_bulk_create_accepts_plain_dicts_and_raises_integrity_error(
    db_session: AsyncSession,
):
    with pytest.raises(HTTPException) as exc_info:
        await item_crud.bulk_create(db_session, [{"name": "No Type"}])
    assert exc_info.value.status_code == 400


async def test_bulk_create_wraps_generic_db_error_as_500(
    db_session: AsyncSession, monkeypatch
):
    async def broken_commit():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(HTTPException) as exc_info:
        await item_crud.bulk_create(
            db_session, [ItemCreate(name="X", item_type=ItemType.WEAPON)]
        )
    assert exc_info.value.status_code == 500
