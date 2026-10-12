from sqlmodel import Session, select

from app.models.product import Product


# Demo prices use integer paise: 29900 is INR 299.00.
LEGACY_PRODUCTS = (
    {"name": "Classic Notebook", "price_paise": 14900, "in_stock": True},
    {"name": "Ballpoint Pen Set", "price_paise": 9900, "in_stock": True},
    {"name": "Ceramic Coffee Mug", "price_paise": 29900, "in_stock": True},
    {"name": "Stainless Steel Water Bottle", "price_paise": 59900, "in_stock": True},
    {"name": "Cotton Tote Bag", "price_paise": 24900, "in_stock": True},
    {"name": "Cotton T-Shirt", "price_paise": 49900, "in_stock": True},
    {"name": "Wireless Mouse", "price_paise": 79900, "in_stock": True},
    {"name": "USB-C Charging Cable", "price_paise": 19900, "in_stock": True},
    {"name": "LED Desk Lamp", "price_paise": 129900, "in_stock": True},
    {"name": "Yoga Mat", "price_paise": 89900, "in_stock": True},
    {"name": "Scented Candle", "price_paise": 34900, "in_stock": True},
    {"name": "Bluetooth Speaker", "price_paise": 149900, "in_stock": False},
)

BOOK_TITLES = (
    "A Light in the Attic", "Tipping the Velvet", "Soumission", "Sharp Objects",
    "Sapiens: A Brief History of Humankind", "The Requiem Red",
    "The Dirty Little Secrets of Getting Your Dream Job",
    "The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull",
    "The Boys in the Boat: Nine Americans and Their Epic Quest for Gold at the 1936 Berlin Olympics",
    "The Black Maria", "Starving Hearts (Triangular Trade Trilogy, #1)", "Shakespeare's Sonnets",
)
SAMPLE_PRODUCTS = tuple(
    {**data, "name": title} for data, title in zip(LEGACY_PRODUCTS, BOOK_TITLES)
)


def seed_sample_products(session: Session) -> int:
    """Migrate old demo titles in place, then insert missing demo books."""
    # Serialize startup seeding across processes using the app's SQLite database.
    session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    existing = session.exec(select(Product)).all()
    existing_names = {item.name.strip().casefold() for item in existing}
    replacements = {old["name"].casefold(): new["name"]
                    for old, new in zip(LEGACY_PRODUCTS, SAMPLE_PRODUCTS)}
    for product in existing:
        new_name = replacements.get(product.name.strip().casefold())
        if new_name and new_name.casefold() not in existing_names:
            existing_names.discard(product.name.strip().casefold())
            product.name = new_name
            session.add(product)
            existing_names.add(new_name.casefold())
    added = 0
    for data in SAMPLE_PRODUCTS:
        if data["name"].casefold() not in existing_names:
            session.add(Product(**data))
            added += 1
    session.commit()
    return added
