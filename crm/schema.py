import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from decimal import Decimal
import re
from .models import Customer, Product, Order


# GraphQL Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = '__all__'


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = '__all__'


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = '__all__'


# Input Types
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()


# Utility Functions
def validate_email(email):
    """Validate email format"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def validate_phone(phone):
    """Validate phone format"""
    if not phone:
        return True
    phone_regex = r'^\+?[\d\-\s\(\)]+$'
    return re.match(phone_regex, phone) is not None


# Mutations
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        errors = []
        
        # Validate email format
        if not validate_email(input.email):
            errors.append("Invalid email format")
        
        # Validate phone format
        if input.phone and not validate_phone(input.phone):
            errors.append("Invalid phone format. Use formats like +1234567890 or 123-456-7890")
        
        # Check for existing email
        if Customer.objects.filter(email=input.email).exists():
            errors.append("Email already exists")
        
        if errors:
            return CreateCustomer(
                customer=None,
                message="Validation failed",
                success=False,
                errors=errors
            )
        
        try:
            customer = Customer.objects.create(
                name=input.name,
                email=input.email,
                phone=input.phone or None
            )
            return CreateCustomer(
                customer=customer,
                message="Customer created successfully",
                success=True,
                errors=[]
            )
        except Exception as e:
            return CreateCustomer(
                customer=None,
                message="Failed to create customer",
                success=False,
                errors=[str(e)]
            )


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)
    success_count = graphene.Int()
    total_count = graphene.Int()

    @staticmethod
    def mutate(root, info, input):
        created_customers = []
        errors = []
        
        with transaction.atomic():
            for i, customer_data in enumerate(input):
                try:
                    # Validate email format
                    if not validate_email(customer_data.email):
                        errors.append(f"Row {i+1}: Invalid email format")
                        continue
                    
                    # Validate phone format
                    if customer_data.phone and not validate_phone(customer_data.phone):
                        errors.append(f"Row {i+1}: Invalid phone format")
                        continue
                    
                    # Check for existing email
                    if Customer.objects.filter(email=customer_data.email).exists():
                        errors.append(f"Row {i+1}: Email {customer_data.email} already exists")
                        continue
                    
                    # Check for duplicate emails in the current batch
                    emails_in_batch = [c.email for c in input[:i]]
                    if customer_data.email in emails_in_batch:
                        errors.append(f"Row {i+1}: Duplicate email {customer_data.email} in batch")
                        continue
                    
                    customer = Customer.objects.create(
                        name=customer_data.name,
                        email=customer_data.email,
                        phone=customer_data.phone or None
                    )
                    created_customers.append(customer)
                    
                except Exception as e:
                    errors.append(f"Row {i+1}: {str(e)}")
        
        return BulkCreateCustomers(
            customers=created_customers,
            errors=errors,
            success_count=len(created_customers),
            total_count=len(input)
        )


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        errors = []
        
        # Validate price
        if input.price <= 0:
            errors.append("Price must be positive")
        
        # Validate stock
        stock = input.stock if input.stock is not None else 0
        if stock < 0:
            errors.append("Stock cannot be negative")
        
        if errors:
            return CreateProduct(
                product=None,
                message="Validation failed",
                success=False,
                errors=errors
            )
        
        try:
            product = Product.objects.create(
                name=input.name,
                price=input.price,
                stock=stock
            )
            return CreateProduct(
                product=product,
                message="Product created successfully",
                success=True,
                errors=[]
            )
        except Exception as e:
            return CreateProduct(
                product=None,
                message="Failed to create product",
                success=False,
                errors=[str(e)]
            )


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        errors = []
        
        # Validate customer exists
        try:
            customer = Customer.objects.get(id=input.customer_id)
        except Customer.DoesNotExist:
            errors.append(f"Customer with ID {input.customer_id} does not exist")
            customer = None
        
        # Validate products exist and get them
        products = []
        if input.product_ids:
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    products.append(product)
                except Product.DoesNotExist:
                    errors.append(f"Product with ID {product_id} does not exist")
        else:
            errors.append("At least one product must be selected")
        
        if errors:
            return CreateOrder(
                order=None,
                message="Validation failed",
                success=False,
                errors=errors
            )
        
        try:
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    customer=customer,
                    order_date=input.order_date
                )
                
                # Add products
                order.products.set(products)
                
                # Calculate and save total amount
                order.calculate_total()
                order.save()
                
                return CreateOrder(
                    order=order,
                    message="Order created successfully",
                    success=True,
                    errors=[]
                )
        except Exception as e:
            return CreateOrder(
                order=None,
                message="Failed to create order",
                success=False,
                errors=[str(e)]
            )


# Query
class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    customer = graphene.Field(CustomerType, id=graphene.ID())
    products = graphene.List(ProductType)
    product = graphene.Field(ProductType, id=graphene.ID())
    orders = graphene.List(OrderType)
    order = graphene.Field(OrderType, id=graphene.ID())

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_customer(self, info, id):
        try:
            return Customer.objects.get(id=id)
        except Customer.DoesNotExist:
            return None

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_product(self, info, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            return None

    def resolve_orders(self, info):
        return Order.objects.all()

    def resolve_order(self, info, id):
        try:
            return Order.objects.get(id=id)
        except Order.DoesNotExist:
            return None


# Mutation
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()