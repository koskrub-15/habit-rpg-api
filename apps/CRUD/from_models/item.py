from apps.CRUD.base import BaseCRUD
from apps.models.item import Item
from apps.schemas.item import ItemCreate, ItemUpdate


class CRUDItem(BaseCRUD[Item, ItemCreate, ItemUpdate]):
    def __init__(self):
        super().__init__(model=Item)


item_crud = CRUDItem()
