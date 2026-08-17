# Sprint 6 normalized property domain

Sprint 6 adopts the pre-existing normalized property schema in `fiftyoneyards`; it does not replace it with a wide property table. Sprint 5 authentication remains the ownership and authorization foundation.

## Aggregate mapping

```text
User -> properties
        |-> property_location -> State -> City -> Locality
        |-> property_sell_details       (SELL)
        |-> property_rent_details       (RENT)
        |-> property_lease_details      (LEASE)
        |-> property_amenities -> amenities_master
        `-> property_status_history
```

The API presents one property resource while the service composes these physical tables transactionally. `properties.property_id` remains the internal key, `properties.user_id` remains the owner key, and the migration adds a UUID `public_id` for external use.

SELL price maps to `expected_price`, RENT price to `monthly_rent`, and LEASE price to `lease_amount`. Location is stored in `property_location`; master foreign keys are added alongside retained legacy text fields. Amenities use the authoritative `amenities_master` table.

## Migration safety

Revision `20260816_02` requires the normalized baseline and fails its preflight if required tables or identity columns are absent. It creates only `states`, `cities`, `localities`, and `property_categories`. It extends existing property types, amenities, property, location, purpose-detail, amenity-map, and history tables with staged additions.

The status enum is expanded to the union of legacy and Sprint 6 values so `INACTIVE`, `SOLD`, and `RENTED` remain readable. Area units likewise retain `SQFT` and `SQM` while adding Sprint 6 values. The downgrade never drops adopted legacy tables and intentionally does not narrow these enums, because doing so could invalidate data created after upgrade.

Before applying to a real database, clone its structure and current Alembic revision, run the migration and seed twice on that clone, and verify constraints and row preservation. MySQL DDL is non-transactional, so backups and a maintenance window remain operational prerequisites.

## Lifecycle and API

Owners can create drafts, list their properties, retrieve private properties, update `DRAFT` or `REJECTED` properties, submit to `PENDING_REVIEW`, and archive without physical deletion. Non-owners can retrieve only `ACTIVE` properties. Creation, related normalized rows, amenities, and initial history are one transaction.

Public master-data and protected property endpoints are documented in OpenAPI under `Master Data` and `Properties`. Search, media handling, contacts, PG behavior, the active-listing index, and other Sprint 7+ functionality remain deferred even though legacy tables for some of those concepts already exist.

## Seed

```powershell
python -m app.scripts.seed_master_data
```

The explicit idempotent seed populates six states, eight cities, thirteen localities, three categories, twelve property types, and nine rows in `amenities_master`. It is not run during application startup.
