from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.master_data import Amenity, City, Locality, PropertyCategory, PropertyType, State


class MasterDataRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def states(self) -> list[State]:
        return list(self.session.scalars(select(State).where(State.is_active).order_by(State.name)))

    def cities(self, state_id: int | None = None) -> list[City]:
        query = select(City).where(City.is_active)
        if state_id is not None:
            query = query.where(City.state_id == state_id)
        return list(self.session.scalars(query.order_by(City.name)))

    def localities(self, city_id: int | None = None) -> list[Locality]:
        query = select(Locality).where(Locality.is_active)
        if city_id is not None:
            query = query.where(Locality.city_id == city_id)
        return list(self.session.scalars(query.order_by(Locality.name)))

    def categories(self) -> list[PropertyCategory]:
        query = (
            select(PropertyCategory)
            .where(PropertyCategory.is_active)
            .order_by(PropertyCategory.sort_order, PropertyCategory.name)
        )
        return list(self.session.scalars(query))

    def types(self, category_id: int | None = None) -> list[PropertyType]:
        query = select(PropertyType).where(PropertyType.is_active)
        if category_id is not None:
            query = query.where(PropertyType.category_id == category_id)
        return list(
            self.session.scalars(query.order_by(PropertyType.sort_order, PropertyType.name))
        )

    def amenities(self) -> list[Amenity]:
        query = select(Amenity).where(Amenity.is_active).order_by(Amenity.sort_order, Amenity.name)
        return list(self.session.scalars(query))

    def state(self, item_id: int) -> State | None:
        return self.session.get(State, item_id)

    def city(self, item_id: int) -> City | None:
        return self.session.get(City, item_id)

    def locality(self, item_id: int) -> Locality | None:
        return self.session.get(Locality, item_id)

    def category(self, item_id: int) -> PropertyCategory | None:
        return self.session.get(PropertyCategory, item_id)

    def property_type(self, item_id: int) -> PropertyType | None:
        return self.session.get(PropertyType, item_id)

    def amenities_by_ids(self, ids: list[int]) -> list[Amenity]:
        if not ids:
            return []
        return list(self.session.scalars(select(Amenity).where(Amenity.id.in_(ids))))
