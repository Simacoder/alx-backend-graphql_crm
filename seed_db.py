import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql.settings")

django.setup()

from crm.models import Customer, Product, Order  # noqa
from django.utils import timezone

def run():
    # Customers
    c1, _ = Customer.objects.get_or_create(name="Alice", email="alice@example.com", defaults={"phone": "+1234567890"})
    c2, _ = Customer.objects.get_or_create(name="Bob", email="bob@example.com", defaults={"phone": "123-456-7890"})

    # Products
    p1, _ = Product.objects.get_or_create(name="Laptop", defaults={"price": Decimal("999.99"), "stock": 10})
    p2, _ = Product.objects.get_or_create(name="Mouse", defaults={"price": Decimal("25.50"), "stock": 100})
    p3, _ = Product.objects.get_or_create(name="Keyboard", defaults={"price": Decimal("45.00"), "stock": 50})

    # One sample order
    o = Order.objects.create(customer=c1, order_date=timezone.now())
    o.products.set([p1, p2, p3])
    o.total_amount = sum([p.price for p in [p1, p2, p3]])
    o.save()

    print("Seeded customers, products, and one order.")

if __name__ == "__main__":
    run()
