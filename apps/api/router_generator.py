"""
Factory for generating FastAPI CRUD routers
Eliminates code duplication for standard operations
"""

from typing import Any, Generic, List, Optional, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.db.session import get_db

CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)
ResponseShortSchemaType = TypeVar("ResponseShortSchemaType", bound=BaseModel)


class RouterFactory(
    Generic[
        CreateSchemaType, UpdateSchemaType, ResponseSchemaType, ResponseShortSchemaType
    ]
):
    """
    Factory for creating standard CRUD routers

    Usage example:
        factory = RouterFactory(
            crud=plot_crud,
            create_schema=PlotCreate,
            update_schema=PlotUpdate,
            response_schema=PlotResponse,
            response_short_schema=PlotResponseShort,
            resource_name="plots",
            resource_name_plural="plots",
            tag="plots"
        )
        router = factory.create_router()
    """

    def __init__(
        self,
        crud: Any,
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        response_schema: Type[ResponseSchemaType],
        response_short_schema: Type[ResponseShortSchemaType],
        resource_name: str,
        resource_name_plural: str,
        tag: str,
        prefix: str = "",
        with_relations_method: Optional[str] = None,
        with_relations_method_multi: Optional[str] = None,
        related_resources: Optional[dict] = None,
        bulk_create_limit: int = 100,
    ):
        prefix = prefix.rstrip("/")
        self.crud = crud
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.response_short_schema = response_short_schema
        self.resource_name = resource_name
        self.resource_name_plural = resource_name_plural
        self.tag = tag
        self.prefix = prefix
        self.with_relations_method = with_relations_method
        self.with_relations_method_multi = with_relations_method_multi
        self.related_resources = related_resources or {}
        self.bulk_create_limit = bulk_create_limit

        self.router = APIRouter(prefix=prefix, tags=[tag])

    def create_router(self) -> APIRouter:
        """Creates a router with all standard endpoints"""
        self._add_create_endpoint()
        self._add_list_endpoint()
        self._add_count_endpoint()
        self._add_get_endpoint()
        self._add_update_endpoint()
        self._add_delete_endpoint()
        self._add_exists_endpoint()
        self._add_bulk_create_endpoint()

        if self.related_resources:
            self._add_related_resources_endpoints()

        return self.router

    def _add_create_endpoint(self):
        """POST / - create resource"""

        @self.router.post(
            "/",
            response_model=self.response_schema,
            status_code=status.HTTP_201_CREATED,
            summary=f"Create a new {self.resource_name}",
        )
        async def create_resource(
            resource_in: self.create_schema, db: AsyncSession = Depends(get_db)
        ):
            f"""Create a new {self.resource_name}"""
            resource = await self.crud.create(db, resource_in)

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                return await method(db, resource.id)
            else:
                return resource

    def _add_list_endpoint(self):
        """GET / - list resources"""

        @self.router.get(
            "/",
            response_model=List[self.response_short_schema],
            summary=f"Get list of all {self.resource_name_plural}",
        )
        async def get_resources(
            skip: int = Query(0, ge=0, description="Number of records to skip"),
            limit: int = Query(
                100, ge=1, le=1000, description="Maximum number of records"
            ),
            name: Optional[str] = Query(
                None, description="Filter by name (partial match)"
            ),
            order_by: Optional[str] = Query(
                "-created_at", description="Sort order (e.g., 'name', '-created_at')"
            ),
            db: AsyncSession = Depends(get_db),
        ):
            f"""
            Get a list of {self.resource_name_plural} with pagination and filtering.

            Sort parameters:
            - `name` - by name (A-Z)
            - `-name` - by name (Z-A)
            - `created_at` - by creation date (old → new)
            - `-created_at` - by creation date (new → old)
            """
            search_fields = {}
            if name:
                search_fields["name"] = name

            order_fields = [order_by] if order_by else None

            resources = await self.crud.get_multi(
                db,
                skip=skip,
                limit=limit,
                search_fields=search_fields,
                order_by=order_fields,
            )
            return resources

    def _add_count_endpoint(self):
        """GET /count - resource count"""

        @self.router.get(
            "/count", response_model=dict, summary=f"Get {self.resource_name} count"
        )
        async def count_resources(db: AsyncSession = Depends(get_db)):
            f"""Get total number of {self.resource_name_plural}"""
            count = await self.crud.count(db)
            return {"count": count}

    def _add_get_endpoint(self):
        """GET /{id} - get a single resource"""

        @self.router.get(
            "/{id}",
            response_model=self.response_schema,
            summary=f"Get {self.resource_name} by ID",
        )
        async def get_resource(id: int, db: AsyncSession = Depends(get_db)):
            f"""Get detailed information about a {self.resource_name} by ID"""

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource = await method(db, id)
            else:
                resource = await self.crud.get(db, id)

            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.resource_name.capitalize()} with id {id} not found",
                )

            return resource

    def _add_update_endpoint(self):
        """PATCH /{id} - update resource"""

        @self.router.patch(
            "/{id}",
            response_model=self.response_schema,
            summary=f"Update {self.resource_name}",
        )
        async def update_resource(
            id: int, resource_in: self.update_schema, db: AsyncSession = Depends(get_db)
        ):
            f"""Update {self.resource_name} information. Only specified fields will be updated."""
            resource = await self.crud.update(db, id=id, obj_in=resource_in)

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                return await method(db, resource.id)
            else:
                return resource

    def _add_delete_endpoint(self):
        """DELETE /{id} - delete resource"""

        @self.router.delete(
            "/{id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete {self.resource_name}",
        )
        async def delete_resource(id: int, db: AsyncSession = Depends(get_db)):
            f"""
            Delete {self.resource_name} by ID.

            ⚠️ **Warning**: Deleting will cascade to related resources.
            """
            await self.crud.delete(db, id=id)
            return None

    def _add_exists_endpoint(self):
        """GET /{id}/exists - check existence"""

        @self.router.get(
            "/{id}/exists",
            response_model=dict,
            summary=f"Check if {self.resource_name} exists",
        )
        async def check_exists(id: int, db: AsyncSession = Depends(get_db)):
            f"""Check if a {self.resource_name} with the specified ID exists"""
            exists = await self.crud.exists(db, id)
            return {"exists": exists}

    def _add_bulk_create_endpoint(self):
        """POST /bulk - bulk create"""

        @self.router.post(
            "/bulk",
            response_model=List[self.response_schema],
            status_code=status.HTTP_201_CREATED,
            summary=f"Bulk create {self.resource_name_plural}",
        )
        async def bulk_create_resources(
            resources_in: List[self.create_schema], db: AsyncSession = Depends(get_db)
        ):
            f"""
            Create multiple {self.resource_name_plural} in one request.
            Useful for data import or bulk creation.
            """
            if len(resources_in) > self.bulk_create_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot create more than {self.bulk_create_limit} {self.resource_name_plural} at once",
                )

            resources = await self.crud.bulk_create(db, resources_in)

            if self.with_relations_method_multi:
                method = getattr(self.crud, self.with_relations_method_multi)
                resource_ids = [r.id for r in resources]
                return await method(db, resource_ids)
            else:
                return resources

    def _add_related_resources_endpoints(self):
        """Add endpoints for related resources (e.g., /plots/{id}/chapters)"""
        for related_name, method_name in self.related_resources.items():
            self._create_related_endpoint(related_name, method_name)

    def _create_related_endpoint(self, related_name: str, method_name: str):
        """Create an endpoint for getting related resources"""

        @self.router.get(
            "/{id}/" + related_name,
            response_model=List[dict],
            summary=f"Get {self.resource_name} {related_name}",
        )
        async def get_related(
            id: int,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000),
            db: AsyncSession = Depends(get_db),
        ):
            f"""Get all {related_name} for a specific {self.resource_name}"""

            method = getattr(self.crud, method_name)
            resource = await method(db, id)

            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.resource_name.capitalize()} with id {id} not found",
                )

            related = getattr(resource, related_name)

            if related_name == "chapters" and related:
                related = sorted(related, key=lambda x: getattr(x, "order", 0))

            return related[skip : skip + limit]
