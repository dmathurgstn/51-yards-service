from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.interfaces import ORMOption

from app.models.property import Property


class PropertyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _options() -> tuple[ORMOption, ...]:
        return (
            selectinload(Property.amenities),
            selectinload(Property.category),
            selectinload(Property.property_type),
            selectinload(Property.location),
            selectinload(Property.sell_details),
            selectinload(Property.rent_details),
            selectinload(Property.lease_details),
        )

    def add(self, item: Property) -> Property:
        self.session.add(item)
        self.session.flush()
        return item

    def by_public_id(self, public_id: str) -> Property | None:
        return self.session.scalar(
            select(Property).options(*self._options()).where(Property.public_id == public_id)
        )

    def owned(self, public_id: str, owner_id: int) -> Property | None:
        return self.session.scalar(
            select(Property)
            .options(*self._options())
            .where(Property.public_id == public_id, Property.owner_user_id == owner_id)
        )

    def list_owned(self, owner_id: int, status: str | None) -> list[Property]:
        query = select(Property).options(*self._options()).where(Property.owner_user_id == owner_id)
        if status is not None:
            query = query.where(Property.status == status)
        return list(self.session.scalars(query.order_by(Property.created_at.desc())))
