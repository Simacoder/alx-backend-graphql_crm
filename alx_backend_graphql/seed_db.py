import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql.settings")
django.setup()

from crm.models import Customer, Product, Order


def seed():
    Customer.objects.all().delete()
    Product.objects.all().delete()
    Order.objects.all().delete()

    # Customers
    alice = Customer.objects.create(name="Alice", email="alice@example.com", phone="+1234567890")
    bob = Customer.objects.create(name="Bob", email="bob@example.com", phone="123-456-7890")

    # Products
    laptop = Product.objects.create(name="Laptop", price=999.99, stock=10)
    phone = Product.objects.create(name="Phone", price=499.99, stock=5)

    # Orders
    order1 = Order.objects.create(customer=alice)
    order1.products.set([laptop, phone])
    order1.calculate_total()

    order2 = Order.objects.create(customer=bob)
    order2.products.set([phone])
    order2.calculate_total()

    print(" Database seeded successfully!")


if __name__ == "__main__":
    seed()
