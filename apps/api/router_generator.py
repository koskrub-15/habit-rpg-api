from typing import List, Optional, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.db.session import get_db

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class RouterFactory:
    def __init__(
        self,
        crud: BaseCRUD,
        create_schema: Type[BaseModel],
        update_schema: Type[BaseModel],
        response_schema: Type[BaseModel],
        resource_name: str,
        resource_name_plural: str,
        tag: str,
        prefix: str = "",
        response_short_schema: Optional[Type[BaseModel]] = None,
        with_relations_method: Optional[str] = None,
        response_schema_relationships: Optional[List[str]] = None,
    ):
        self.crud = crud
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.response_short_schema = response_short_schema or response_schema
        self.resource_name = resource_name
        self.resource_name_plural = resource_name_plural
        self.tag = tag
        self.prefix = prefix
        self.router = APIRouter(prefix=self.prefix, tags=[self.tag])
        self.with_relations_method = with_relations_method
        self.response_schema_relationships = response_schema_relationships or []

    def create_router(self) -> APIRouter:
        self._add_get_all_endpoint()
        self._add_get_one_endpoint()
        self._add_create_endpoint()
        self._add_update_endpoint()
        self._add_delete_endpoint()
        return self.router

    def _add_get_all_endpoint(self):
        """GET / - list all resources"""

        @self.router.get(
            "/",
            response_model=List[self.response_short_schema],  # type: ignore
            summary=f"Get all {self.resource_name_plural}",
        )
        async def get_all(
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=500),
            db: AsyncSession = Depends(get_db),
        ):
            return await self.crud.get_multi(db, skip=skip, limit=limit)

    def _add_get_one_endpoint(self):
        """GET /{id} - get resource by ID"""

        @self.router.get(
            "/{id}",
            response_model=self.response_schema,  # type: ignore
            summary=f"Get {self.resource_name} by ID",
        )
        async def get_one(id: int, db: AsyncSession = Depends(get_db)):
            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource = await method(
                    db, id, relationships=self.response_schema_relationships
                )
            else:
                resource = await self.crud.get(
                    db, id, relationships=self.response_schema_relationships
                )

            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.resource_name.capitalize()} with id {id} not found",
                )

            return resource

    def _add_create_endpoint(self):
        """POST / - create resource"""

        @self.router.post(
            "/",
            response_model=self.response_schema,  # type: ignore
            status_code=status.HTTP_201_CREATED,
            summary=f"Create {self.resource_name}",
        )
        async def create_resource(
            resource_in: self.create_schema,
            db: AsyncSession = Depends(get_db),  # type: ignore
        ):
            resource = await self.crud.create(db, obj_in=resource_in)

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource_with_relations = await method(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            else:
                resource_with_relations = await self.crud.get(
                    db, resource.id, relationships=self.response_schema_relationships
                )

            return resource_with_relations

    def _add_update_endpoint(self):
        """PATCH /{id} - update resource"""

        @self.router.patch(
            "/{id}",
            response_model=self.response_schema,  # type: ignore
            summary=f"Update {self.resource_name}",
        )
        async def update_resource(
            id: int,
            resource_in: self.update_schema,  # type: ignore
            db: AsyncSession = Depends(get_db),
        ):
            f"""Update {self.resource_name} information. Only specified fields will be updated."""
            resource = await self.crud.update(db, id=id, obj_in=resource_in)

            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.resource_name.capitalize()} with id {id} not found",
                )

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource_with_relations = await method(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            else:
                resource_with_relations = await self.crud.get(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            return resource_with_relations

    def _add_delete_endpoint(self):
        """DELETE /{id} - delete resource"""

        @self.router.delete(
            "/{id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete {self.resource_name}",
        )
        async def delete_resource(id: int, db: AsyncSession = Depends(get_db)):
            await self.crud.remove(db, id=id)
            return
