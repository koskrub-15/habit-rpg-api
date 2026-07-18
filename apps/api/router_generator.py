"""
Factory for generating FastAPI CRUD routers
Eliminates code duplication for standard operations
"""

from typing import (
    Any,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.db.session import get_db

CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)
ResponseShortSchemaType = TypeVar("ResponseShortSchemaType", bound=BaseModel)


def _is_superuser(user: Any) -> bool:
    """Return True if the authenticated user has the superuser flag set."""
    return bool(getattr(user, "is_superuser", False))


def _get_relationship_names_from_schema(schema: Type[BaseModel]) -> List[str]:
    """
    Analyzes a Pydantic schema to identify field names that represent relationships.
    Detects fields annotated as:
    - List[PydanticModel]
    - PydanticModel (Optional or not)
    - Optional[List[PydanticModel]]
    Supports string forward references.
    """
    relationships = []
    for field_name, field_info in schema.model_fields.items():
        annotation = field_info.annotation

        def is_model_type(tp):
            # Unwrap Optional/Union
            if get_origin(tp) is Union:
                return any(is_model_type(arg) for arg in get_args(tp))

            # Check for List
            if get_origin(tp) is list:
                return is_model_type(get_args(tp)[0])

            # Check for BaseModel subclass
            if isinstance(tp, type) and issubclass(tp, BaseModel):
                return True

            # Check for string or ForwardRef (likely a Pydantic model in our schemas)
            if isinstance(tp, str) or "ForwardRef" in str(type(tp)):
                # Exclude basic types if they appear as strings for some reason
                if tp in ("int", "str", "float", "bool", "datetime"):
                    return False
                return True

            return False

        if is_model_type(annotation):
            # Exclude fields that are clearly not ORM relationships but might use Pydantic models
            # In this project, most such fields ARE relationships.
            # Basic types like int, str etc are not detected by is_model_type.
            relationships.append(field_name)

    return relationships


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
            tag="plots",
            current_user_dependency=Depends(get_current_user)
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
        current_user_dependency: Optional[Any] = None,
        owner_field: Optional[str] = None,
        write_requires_superuser: bool = False,
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
        self.current_user_dependency = current_user_dependency
        self.owner_field = owner_field
        self.write_requires_superuser = write_requires_superuser

        self.router = APIRouter(prefix=prefix, tags=[tag])

        self.response_schema_relationships = _get_relationship_names_from_schema(
            response_schema
        )
        self.response_short_schema_relationships = _get_relationship_names_from_schema(
            response_short_schema
        )

    def create_router(self) -> APIRouter:
        """Generate and return a router with all standard endpoints"""
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

    def _add_related_resources_endpoints(self) -> None:
        pass

    def _owner_filter(self, current_user: Any) -> dict:
        """Restrict list/count queries to the caller's own rows.

        Returns an empty filter for superusers, unauthenticated routers, or
        resources that are not user-owned, so they see everything.
        """
        if self.owner_field and current_user and not _is_superuser(current_user):
            return {self.owner_field: current_user.id}
        return {}

    def _check_owner(self, obj: Any, current_user: Any) -> None:
        """Raise 403 when a non-superuser touches a row they do not own."""
        if not self.owner_field or current_user is None or _is_superuser(current_user):
            return
        if getattr(obj, self.owner_field, None) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions to access this {self.resource_name}",
            )

    def _require_superuser(self, current_user: Any) -> None:
        """Raise 403 when a non-superuser attempts a superuser-only action."""
        if current_user is not None and not _is_superuser(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser privileges required",
            )

    def _check_write_permission(self, existing: Any, current_user: Any) -> None:
        """Authorize an update/delete on an existing row."""
        if self.owner_field:
            self._check_owner(existing, current_user)
        elif self.write_requires_superuser:
            self._require_superuser(current_user)

    def _apply_owner_on_create(self, resource_in: Any, current_user: Any) -> None:
        """Force a non-superuser's new rows to be owned by themselves."""
        if (
            self.owner_field
            and current_user
            and not _is_superuser(current_user)
            and hasattr(resource_in, self.owner_field)
        ):
            setattr(resource_in, self.owner_field, current_user.id)

    def _add_create_endpoint(self):
        """POST / - create resource"""

        @self.router.post(
            "/",
            response_model=self.response_schema,  # type: ignore
            status_code=status.HTTP_201_CREATED,
            summary=f"Create a new {self.resource_name}",
        )
        async def create_resource(
            resource_in: self.create_schema,  # type: ignore
            db: AsyncSession = Depends(get_db),
            current_user: Any = self.current_user_dependency,
        ):
            f"""Create a new {self.resource_name}"""
            if self.write_requires_superuser:
                self._require_superuser(current_user)
            self._apply_owner_on_create(resource_in, current_user)

            resource = await self.crud.create(db, resource_in)

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource_with_relations = await method(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            else:
                resource_with_relations = await self.crud.get(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            return self.response_schema.model_validate(resource_with_relations)

    def _add_list_endpoint(self):
        """GET / - list resources"""

        @self.router.get(
            "/",
            response_model=List[self.response_short_schema],  # type: ignore
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
            current_user: Any = self.current_user_dependency,
        ):
            f"""
            Get a list of {self.resource_name_plural} with pagination and filtering.
            """
            search_fields = {}
            if name:
                search_fields["name"] = name

            order_fields = [order_by] if order_by else None

            resources = await self.crud.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=self._owner_filter(current_user),
                search_fields=search_fields,
                order_by=order_fields,
                relationships=self.response_short_schema_relationships,
            )
            return [self.response_short_schema.model_validate(r) for r in resources]

    def _add_count_endpoint(self):
        """GET /count - resource count"""

        @self.router.get(
            "/count", response_model=dict, summary=f"Get {self.resource_name} count"
        )
        async def count_resources(
            db: AsyncSession = Depends(get_db),
            current_user: Any = self.current_user_dependency,
        ):
            f"""Get total number of {self.resource_name_plural}"""
            count = await self.crud.count(db, filters=self._owner_filter(current_user))
            return {"count": count}

    def _add_get_endpoint(self):
        """GET /{id} - get a single resource"""

        @self.router.get(
            "/{id}",
            response_model=self.response_schema,  # type: ignore
            summary=f"Get {self.resource_name} by ID",
        )
        async def get_resource(
            id: int,
            db: AsyncSession = Depends(get_db),
            current_user: Any = self.current_user_dependency,
        ):
            f"""Get detailed information about a {self.resource_name} by ID"""

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource_with_relations = await method(
                    db, id, relationships=self.response_schema_relationships
                )
            else:
                resource_with_relations = await self.crud.get(
                    db, id, relationships=self.response_schema_relationships
                )

            if not resource_with_relations:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.resource_name.capitalize()} with id {id} not found",
                )

            self._check_owner(resource_with_relations, current_user)

            return self.response_schema.model_validate(resource_with_relations)

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
            current_user: Any = self.current_user_dependency,
        ):
            f"""Update {self.resource_name} information. Only specified fields will be updated."""
            existing = await self.crud.get(db, id, raise_not_found=True)
            self._check_write_permission(existing, current_user)

            resource = await self.crud.update(db, id=id, obj_in=resource_in)

            if self.with_relations_method:
                method = getattr(self.crud, self.with_relations_method)
                resource_with_relations = await method(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            else:
                resource_with_relations = await self.crud.get(
                    db, resource.id, relationships=self.response_schema_relationships
                )
            return self.response_schema.model_validate(resource_with_relations)

    def _add_delete_endpoint(self):
        """DELETE /{id} - delete resource"""

        @self.router.delete(
            "/{id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete {self.resource_name}",
        )
        async def delete_resource(
            id: int,
            db: AsyncSession = Depends(get_db),
            current_user: Any = self.current_user_dependency,
        ):
            f"""
            Delete {self.resource_name} by ID.
            """
            existing = await self.crud.get(db, id, raise_not_found=True)
            self._check_write_permission(existing, current_user)

            await self.crud.delete(db, id=id)
            return None

    def _add_exists_endpoint(self):
        """GET /{id}/exists - check existence"""

        @self.router.get(
            "/{id}/exists",
            response_model=dict,
            summary=f"Check if {self.resource_name} exists",
        )
        async def check_exists(
            id: int,
            db: AsyncSession = Depends(get_db),
            current_user: Any = self.current_user_dependency,
        ):
            f"""Check if a {self.resource_name} with the specified ID exists"""
            resource = await self.crud.get(db, id)
            if (
                resource
                and self.owner_field
                and current_user
                and not _is_superuser(current_user)
                and getattr(resource, self.owner_field, None) != current_user.id
            ):
                return {"exists": False}
            return {"exists": resource is not None}

    def _add_bulk_create_endpoint(self):
        """POST /bulk - bulk create"""

        @self.router.post(
            "/bulk",
            response_model=List[self.response_schema],  # type: ignore
            status_code=status.HTTP_201_CREATED,
            summary=f"Bulk create {self.resource_name_plural}",
        )
        async def bulk_create_resources(
            resources_in: List[self.create_schema],  # type: ignore
            db: AsyncSession = Depends(get_db),
            current_user: Any = self.current_user_dependency,
        ):
            f"""
            Create multiple {self.resource_name_plural} in one request.
            """
            if len(resources_in) > self.bulk_create_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot create more than {self.bulk_create_limit} {self.resource_name_plural} at once",
                )

            if self.write_requires_superuser:
                self._require_superuser(current_user)
            for res_in in resources_in:
                self._apply_owner_on_create(res_in, current_user)

            resources = await self.crud.bulk_create(db, resources_in)

            if self.with_relations_method_multi:
                method = getattr(self.crud, self.with_relations_method_multi)
                resource_ids = [r.id for r in resources]
                resources_with_relations = await method(
                    db, resource_ids, relationships=self.response_schema_relationships
                )
                return [
                    self.response_schema.model_validate(r)
                    for r in resources_with_relations
                ]
            else:
                resources_with_relations = []
                for res in resources:
                    full_res = await self.crud.get(
                        db, res.id, relationships=self.response_schema_relationships
                    )
                    if full_res:
                        resources_with_relations.append(full_res)
                return [
                    self.response_schema.model_validate(r)
                    for r in resources_with_relations
                ]
