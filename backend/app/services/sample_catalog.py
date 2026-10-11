from sqlmodel import Session, select

from app.models.product import Product


# Demo prices use integer paise: 29900 is INR 299.00.
SAMPLE_PRODUCTS = (
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


def seed_sample_products(session: Session) -> int:
    """Insert missing demo products without replacing existing catalog data."""
    # Serialize startup seeding across processes using the app's SQLite database.
    session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    existing_names = {
        name.strip().casefold() for name in session.exec(select(Product.name)).all()
    }
    added = 0
    for data in SAMPLE_PRODUCTS:
        if data["name"].casefold() not in existing_names:
            session.add(Product(**data))
            added += 1
    session.commit()
    return added
