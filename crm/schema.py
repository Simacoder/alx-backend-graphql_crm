import re
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.utils import timezone

import graphene
from graphene_django import DjangoObjectType

from .models import Customer, Product, Order


# ========== GraphQL Types ==========
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# ========== Inputs ==========
class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    # graphene.Decimal works with Django DecimalField
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)


class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)           # appears as customerId in GraphQL
    product_ids = graphene.List(graphene.ID, required=True)  # appears as productIds
    order_date = graphene.DateTime(required=False)     # optional


# ========== Validators ==========
PHONE_RE = re.compile(r'^(\+\d{7,15}|\d{3}-\d{3}-\d{4})$')  # +1234567890 or 123-456-7890


def validate_phone(phone: str) -> bool:
    if phone in (None, "",):
        return True
    return bool(PHONE_RE.match(phone))


# ========== Mutations ==========
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateCustomerInput):
        name = (input.get("name") or "").strip()
        email = (input.get("email") or "").strip().lower()
        phone = (input.get("phone") or None)

        errs = []
        if not name:
            errs.append("Name is required.")
        if not email:
            errs.append("Email is required.")
        if phone and not validate_phone(phone):
            errs.append("Invalid phone format. Use +1234567890 or 123-456-7890.")

        if Customer.objects.filter(email=email).exists():
            errs.append("Email already exists.")

        if errs:
            return CreateCustomer(customer=None, message="Failed to create customer.", errors=errs)

        c = Customer.objects.create(name=name, email=email, phone=phone)
        return CreateCustomer(customer=c, message="Customer created successfully.", errors=[])


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CreateCustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        created_customers = []
        error_msgs = []

        # Single outer transaction; use savepoints for partial success per record
        with transaction.atomic():
            for idx, item in enumerate(input):
                name = (item.get("name") or "").strip()
                email = (item.get("email") or "").strip().lower()
                phone = (item.get("phone") or None)
                local_errs = []

                if not name:
                    local_errs.append("Name is required.")
                if not email:
                    local_errs.append("Email is required.")
                if phone and not validate_phone(phone):
                    local_errs.append("Invalid phone format. Use +1234567890 or 123-456-7890.")
                if Customer.objects.filter(email=email).exists():
                    local_errs.append("Email already exists.")

                if local_errs:
                    error_msgs.append(f"Index {idx}: {', '.join(local_errs)}")
                    continue

                sid = transaction.savepoint()
                try:
                    c = Customer.objects.create(name=name, email=email, phone=phone)
                    transaction.savepoint_commit(sid)
                    created_customers.append(c)
                except IntegrityError:
                    transaction.savepoint_rollback(sid)
                    error_msgs.append(f"Index {idx}: Email already exists.")
                except Exception as e:
                    transaction.savepoint_rollback(sid)
                    error_msgs.append(f"Index {idx}: {str(e)}")

        return BulkCreateCustomers(customers=created_customers, errors=error_msgs)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateProductInput):
        name = (input.get("name") or "").strip()
        price = input.get("price")
        stock = input.get("stock", 0)

        errs = []
        if not name:
            errs.append("Name is required.")
        try:
            price = Decimal(price)
            if price <= 0:
                errs.append("Price must be positive.")
        except Exception:
            errs.append("Price must be a valid decimal number.")
        try:
            stock = int(stock or 0)
            if stock < 0:
                errs.append("Stock cannot be negative.")
        except Exception:
            errs.append("Stock must be an integer.")

        if errs:
            return CreateProduct(product=None, errors=errs)

        p = Product.objects.create(name=name, price=price, stock=stock)
        return CreateProduct(product=p, errors=[])


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateOrderInput):
        errs = []

        # Validate customer
        customer_id = input.get("customer_id")
        try:
            customer_id_int = int(customer_id)
            customer = Customer.objects.get(pk=customer_id_int)
        except (ValueError, TypeError):
            errs.append("Invalid customer ID.")
            customer = None
        except Customer.DoesNotExist:
            errs.append("Customer not found.")
            customer = None

        # Validate products
        product_ids = input.get("product_ids") or []
        products = []
        if not product_ids:
            errs.append("At least one product must be selected.")
        else:
            for pid in product_ids:
                try:
                    p = Product.objects.get(pk=int(pid))
                    products.append(p)
                except (ValueError, TypeError):
                    errs.append(f"Invalid product ID: {pid}")
                except Product.DoesNotExist:
                    errs.append(f"Product not found: {pid}")

        # order date
        order_date = input.get("order_date") or timezone.now()

        if errs:
            return CreateOrder(order=None, errors=errs)

        # Create order and compute total with atomicity
        with transaction.atomic():
            order = Order.objects.create(customer=customer, order_date=order_date)
            # attach products
            order.products.set(products)
            # compute total
            total = sum((p.price for p in products), Decimal("0.00"))
            order.total_amount = total
            order.save()

        return CreateOrder(order=order, errors=[])


# ========== Query ==========
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(root, info):
        return Customer.objects.all()

    def resolve_products(root, info):
        return Product.objects.all()

    def resolve_orders(root, info):
        return Order.objects.select_related("customer").prefetch_related("products")


# ========== Mutation Root ==========
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
