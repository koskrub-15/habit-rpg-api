import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, selectinload

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

DATABASE_ERROR_MESSAGE = "Database error occurred"


class CRUDException(Exception):
    """Base exception for CRUD operations"""

    pass


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base CRUD class with extended functionality

    Args:
        model: SQLAlchemy model
        id_field: ID field name (default 'id')
    """

    def __init__(self, model: Type[ModelType], id_field: str = "id"):
        self.model = model
        self.id_field = id_field

    async def create(
        self,
        db: AsyncSession,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        commit: bool = True,
    ) -> ModelType:
        """
        Create a new record

        Args:
            db: Database session
            obj_in: Pydantic schema or dictionary with data
            commit: Auto commit (default True)
        """
        try:
            if isinstance(obj_in, dict):
                create_data = obj_in
            else:
                create_data = obj_in.model_dump(exclude_unset=True)

            db_obj = self.model(**create_data)
            db.add(db_obj)

            if commit:
                await db.commit()
                await db.refresh(db_obj)
            else:
                await db.flush()

            return db_obj

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database integrity error: {str(e.orig)}",
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        raise_not_found: bool = False,
        relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get record by ID

        Args:
            db: Database session
            id: ID value
            raise_not_found: Raise 404 if not found
            relationships: List of relationships to eagerly load
        """
        try:
            stmt = select(self.model).where(getattr(self.model, self.id_field) == id)
            if relationships:
                for rel in relationships:
                    stmt = stmt.options(selectinload(getattr(self.model, rel)))

            result = await db.execute(stmt)
            obj = result.scalar_one_or_none()

            if obj is None and raise_not_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model.__name__} with {self.id_field}={id} not found",
                )

            return obj

        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
        search_fields: Optional[Dict[str, str]] = None,
        relationships: Optional[List[str]] = None,
    ) -> List[ModelType]:
        """
        Get multiple records with filtering and ordering

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records
            filters: Dictionary of filters {field: value} - exact match or IN for lists
            order_by: List of fields for sorting (prefix '-' for DESC)
            search_fields: Dictionary for LIKE search {field: search_term}
            relationships: List of relationships to eagerly load
        """
        try:
            stmt = select(self.model)

            if relationships:
                for rel in relationships:
                    stmt = stmt.options(selectinload(getattr(self.model, rel)))

            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            conditions.append(getattr(self.model, field).in_(value))
                        else:
                            conditions.append(getattr(self.model, field) == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            if search_fields:
                search_conditions = []
                for field, search_term in search_fields.items():
                    if hasattr(self.model, field):
                        search_conditions.append(
                            getattr(self.model, field).ilike(f"%{search_term}%")
                        )
                if search_conditions:
                    stmt = stmt.where(and_(*search_conditions))

            if order_by:
                for field in order_by:
                    if field.startswith("-"):
                        field_name = field[1:]
                        if hasattr(self.model, field_name):
                            stmt = stmt.order_by(getattr(self.model, field_name).desc())
                    else:
                        if hasattr(self.model, field):
                            stmt = stmt.order_by(getattr(self.model, field))

            stmt = stmt.offset(skip).limit(limit)
            result = await db.execute(stmt)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting multiple {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def update(
        self,
        db: AsyncSession,
        *,
        id: Any,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        commit: bool = True,
    ) -> Optional[ModelType]:
        """
        Update existing record

        Args:
            db: Database session
            id: Record ID
            obj_in: Pydantic schema or dictionary with data
            commit: Auto commit
        """
        try:
            db_obj = await self.get(db, id, raise_not_found=True)

            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            db.add(db_obj)

            if commit:
                await db.commit()
                await db.refresh(db_obj)
            else:
                await db.flush()

            return db_obj

        except HTTPException:
            raise
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database integrity error: {str(e.orig)}",
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def delete(
        self, db: AsyncSession, *, id: Any, commit: bool = True
    ) -> Optional[ModelType]:
        """
        Delete record

        Args:
            db: Database session
            id: Record ID
            commit: Auto commit
        """
        try:
            db_obj = await self.get(db, id, raise_not_found=True)

            stmt = delete(self.model).where(getattr(self.model, self.id_field) == id)
            await db.execute(stmt)

            if commit:
                await db.commit()
            else:
                await db.flush()

            return db_obj

        except HTTPException:
            raise
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error deleting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete: record is referenced by other records",
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error deleting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def exists(self, db: AsyncSession, id: Any) -> bool:
        """Check if a record exists"""
        try:
            obj = await self.get(db, id)
            return obj is not None
        except SQLAlchemyError:
            return False

    async def count(
        self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records

        Args:
            db: Database session
            filters: Dictionary of filters
        """
        try:
            from sqlalchemy import func

            stmt = select(func.count()).select_from(self.model)

            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            conditions.append(getattr(self.model, field).in_(value))
                        else:
                            conditions.append(getattr(self.model, field) == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            result = await db.execute(stmt)
            return result.scalar_one()

        except SQLAlchemyError as e:
            logger.error(f"Database error counting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def get_or_create(
        self, db: AsyncSession, *, defaults: Optional[Dict[str, Any]] = None, **kwargs
    ) -> tuple[ModelType, bool]:
        """
        Get existing or create a new record

        Returns:
            Tuple[ModelType, bool]: (object, was_created)
        """
        try:
            stmt = select(self.model)
            conditions = []
            for field, value in kwargs.items():
                if hasattr(self.model, field):
                    conditions.append(getattr(self.model, field) == value)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            result = await db.execute(stmt)
            obj = result.scalar_one_or_none()

            if obj:
                return obj, False

            create_data = {**kwargs, **(defaults or {})}
            new_obj = await self.create(db, create_data)
            return new_obj, True

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error in get_or_create {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )

    async def bulk_create(
        self,
        db: AsyncSession,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
        commit: bool = True,
        relationships: Optional[List[str]] = None,
    ) -> List[ModelType]:
        """
        Bulk create records

        Args:
            db: Database session
            objs_in: List of schemas or dictionaries
            commit: Auto commit
            relationships: List of relationships to eagerly load
        """
        try:
            db_objs = []
            for obj_in in objs_in:
                if isinstance(obj_in, dict):
                    create_data = obj_in
                else:
                    create_data = obj_in.model_dump(exclude_unset=True)
                db_objs.append(self.model(**create_data))

            db.add_all(db_objs)

            if commit:
                await db.commit()
                ids = [getattr(obj, self.id_field) for obj in db_objs]
                stmt = select(self.model).where(
                    getattr(self.model, self.id_field).in_(ids)
                )
                if relationships:
                    for rel in relationships:
                        stmt = stmt.options(selectinload(getattr(self.model, rel)))
                result = await db.execute(stmt)
                return list(result.scalars().all())

            else:
                await db.flush()
                return db_objs

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Integrity error in bulk create {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database integrity error: {str(e.orig)}",
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error in bulk create {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DATABASE_ERROR_MESSAGE,
            )
