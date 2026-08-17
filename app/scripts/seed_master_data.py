from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import create_session_factory
from app.models.master_data import Amenity, City, Locality, PropertyCategory, PropertyType, State

STATES = [
    ("UP", "Uttar Pradesh"),
    ("DL", "Delhi"),
    ("HR", "Haryana"),
    ("KA", "Karnataka"),
    ("MH", "Maharashtra"),
    ("TG", "Telangana"),
]
CITIES = [
    ("UP", "Noida"),
    ("UP", "Greater Noida"),
    ("UP", "Ghaziabad"),
    ("DL", "New Delhi"),
    ("HR", "Gurugram"),
    ("KA", "Bengaluru"),
    ("MH", "Pune"),
    ("TG", "Hyderabad"),
]
LOCALITIES = {
    "Noida": ["Sector 62", "Sector 76", "Sector 137"],
    "Greater Noida": ["Noida Extension", "Pari Chowk"],
    "Gurugram": ["Sector 56", "Dwarka Expressway"],
    "Bengaluru": ["Whitefield", "Electronic City"],
    "Pune": ["Hinjawadi", "Baner"],
    "Hyderabad": ["Gachibowli", "HITEC City"],
}
CATEGORIES = [("RESIDENTIAL", "Residential"), ("COMMERCIAL", "Commercial"), ("LAND", "Land")]
TYPES = {
    "RESIDENTIAL": ["APARTMENT", "INDEPENDENT_HOUSE", "VILLA", "BUILDER_FLOOR", "STUDIO"],
    "COMMERCIAL": ["OFFICE", "SHOP", "SHOWROOM", "WAREHOUSE"],
    "LAND": ["RESIDENTIAL_PLOT", "COMMERCIAL_LAND", "AGRICULTURAL_LAND"],
}
AMENITIES = [
    "PARKING",
    "LIFT",
    "POWER_BACKUP",
    "SECURITY",
    "GYM",
    "SWIMMING_POOL",
    "CLUB_HOUSE",
    "PARK",
    "CCTV",
]


def slug(value: str) -> str:
    return "-".join(value.lower().split())


def seed(session: Session) -> None:
    for code, name in STATES:
        if session.scalar(select(State).where(State.code == code)) is None:
            session.add(State(code=code, name=name))
    session.flush()
    states = {x.code: x for x in session.scalars(select(State))}
    for state_code, name in CITIES:
        if (
            session.scalar(
                select(City).where(City.state_id == states[state_code].id, City.slug == slug(name))
            )
            is None
        ):
            session.add(City(state_id=states[state_code].id, name=name, slug=slug(name)))
    session.flush()
    cities = {x.name: x for x in session.scalars(select(City))}
    for city_name, names in LOCALITIES.items():
        for name in names:
            if (
                session.scalar(
                    select(Locality).where(
                        Locality.city_id == cities[city_name].id, Locality.slug == slug(name)
                    )
                )
                is None
            ):
                session.add(Locality(city_id=cities[city_name].id, name=name, slug=slug(name)))
    for order, (code, name) in enumerate(CATEGORIES):
        if session.scalar(select(PropertyCategory).where(PropertyCategory.code == code)) is None:
            session.add(PropertyCategory(code=code, name=name, sort_order=order))
    session.flush()
    categories = {x.code: x for x in session.scalars(select(PropertyCategory))}
    for category_code, codes in TYPES.items():
        for order, code in enumerate(codes):
            if session.scalar(select(PropertyType).where(PropertyType.code == code)) is None:
                session.add(
                    PropertyType(
                        category_id=categories[category_code].id,
                        code=code,
                        name=code.replace("_", " ").title(),
                        sort_order=order,
                    )
                )
    for order, code in enumerate(AMENITIES):
        if session.scalar(select(Amenity).where(Amenity.code == code)) is None:
            session.add(Amenity(code=code, name=code.replace("_", " ").title(), sort_order=order))
    session.commit()


def main() -> None:
    with create_session_factory()() as session:
        seed(session)
    print("Master data seed completed.")


if __name__ == "__main__":
    main()
