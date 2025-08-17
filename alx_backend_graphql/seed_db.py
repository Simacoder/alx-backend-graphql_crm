#!/usr/bin/env python
"""
Database seeding script for CRM system
Run this script to populate the database with sample data
"""

import os
import sys
import django
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order


def seed_customers():
    """Create sample customers"""
    print("Seeding customers...")
    
    customers_data = [
        {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '+1-555-0101'
        },
        {
            'name': 'Jane Smith',
            'email': 'jane.smith@example.com',
            'phone': '555-0102'
        },
        {
            'name': 'Bob Johnson',
            'email': 'bob.johnson@example.com',
            'phone': '+1 (555) 0103'
        },
        {
            'name': 'Alice Brown',
            'email': 'alice.brown@example.com',
            'phone': '555.0104'
        },
        {
            'name': 'Charlie Wilson',
            'email': 'charlie.wilson@example.com',
            'phone': None
        },
        {
            'name': 'Diana Davis',
            'email': 'diana.davis@example.com',
            'phone': '+1-555-0106'
        },
    ]
    
    created_customers = []
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            email=customer_data['email'],
            defaults=customer_data
        )
        if created:
            print(f"  Created customer: {customer.name}")
        else:
            print(f"  Customer already exists: {customer.name}")
        created_customers.append(customer)
    
    return created_customers


def seed_products():
    """Create sample products"""
    print("Seeding products...")
    
    products_data = [
        {
            'name': 'MacBook Pro 16"',
            'price': Decimal('2499.99'),
            'stock': 15
        },
        {
            'name': 'iPhone 15 Pro',
            'price': Decimal('999.99'),
            'stock': 50
        },
        {
            'name': 'iPad Air',
            'price': Decimal('599.99'),
            'stock': 30
        },
        {
            'name': 'AirPods Pro',
            'price': Decimal('249.99'),
            'stock': 100
        },
        {
            'name': 'Apple Watch Series 9',
            'price': Decimal('399.99'),
            'stock': 25
        },
        {
            'name': 'Magic Mouse',
            'price': Decimal('79.99'),
            'stock': 40
        },
        {
            'name': 'Magic Keyboard',
            'price': Decimal('179.99'),
            'stock': 35
        },
        {
            'name': 'Studio Display',
            'price': Decimal('1599.99'),
            'stock': 8
        },
        {
            'name': 'Mac Mini M2',
            'price': Decimal('699.99'),
            'stock': 20
        },
        {
            'name': 'HomePod mini',
            'price': Decimal('99.99'),
            'stock': 60
        },
    ]
    
    created_products = []
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            defaults=product_data
        )
        if created:
            print(f"  Created product: {product.name}")
        else:
            print(f"  Product already exists: {product.name}")
        created_products.append(product)
    
    return created_products


def seed_orders(customers, products):
    """Create sample orders"""
    print("Seeding orders...")
    
    import random
    
    # Create orders for the past 30 days
    base_date = timezone.now() - timedelta(days=30)
    
    orders_data = [
        {
            'customer': customers[0],  # John Doe
            'products': [products[0], products[3]],  # MacBook Pro + AirPods Pro
            'days_ago': 1
        },
        {
            'customer': customers[1],  # Jane Smith
            'products': [products[1]],  # iPhone 15 Pro
            'days_ago': 2
        },
        {
            'customer': customers[2],  # Bob Johnson
            'products': [products[2], products[4], products[5]],  # iPad Air + Apple Watch + Magic Mouse
            'days_ago': 5
        },
        {
            'customer': customers[3],  # Alice Brown
            'products': [products[8], products[6], products[7]],  # Mac Mini + Magic Keyboard + Studio Display
            'days_ago': 7
        },
        {
            'customer': customers[4],  # Charlie Wilson
            'products': [products[9], products[9]],  # 2x HomePod mini
            'days_ago': 10
        },
        {
            'customer': customers[0],  # John Doe (repeat customer)
            'products': [products[3]],  # AirPods Pro
            'days_ago': 15
        },
        {
            'customer': customers[5],  # Diana Davis
            'products': [products[1], products[3], products[4]],  # iPhone + AirPods + Apple Watch
            'days_ago': 20
        },
        {
            'customer': customers[2],  # Bob Johnson (repeat customer)
            'products': [products[6]],  # Magic Keyboard
            'days_ago': 25
        },
    ]
    
    created_orders = []
    for i, order_data in enumerate(orders_data):
        # Check if similar order already exists
        existing_order = Order.objects.filter(
            customer=order_data['customer'],
            order_date__date=(base_date + timedelta(days=order_data['days_ago'])).date()
        ).first()
        
        if not existing_order:
            order = Order.objects.create(
                customer=order_data['customer'],
                order_date=base_date + timedelta(days=order_data['days_ago'])
            )
            order.products.set(order_data['products'])
            order.calculate_total()
            order.save()
            
            print(f"  Created order #{order.id} for {order.customer.name} - ${order.total_amount}")
            created_orders.append(order)
        else:
            print(f"  Order already exists for {order_data['customer'].name} on that date")
            created_orders.append(existing_order)
    
    return created_orders


def print_summary():
    """Print database summary"""
    print("\n" + "="*50)
    print("DATABASE SUMMARY")
    print("="*50)
    print(f"Customers: {Customer.objects.count()}")
    print(f"Products: {Product.objects.count()}")
    print(f"Orders: {Order.objects.count()}")
    
    # Show some sample data
    print("\nSample Customers:")
    for customer in Customer.objects.all()[:3]:
        print(f"  - {customer.name} ({customer.email})")
    
    print("\nSample Products:")
    for product in Product.objects.all()[:3]:
        print(f"  - {product.name}: ${product.price} (Stock: {product.stock})")
    
    print("\nSample Orders:")
    for order in Order.objects.all()[:3]:
        products_count = order.products.count()
        print(f"  - Order #{order.id}: {order.customer.name} - {products_count} item(s) - ${order.total_amount}")


def main():
    """Main seeding function"""
    print("Starting database seeding...")
    print("="*50)
    
    try:
        # Seed data
        customers = seed_customers()
        products = seed_products()
        orders = seed_orders(customers, products)
        
        # Print summary
        print_summary()
        
        print("\n" + "="*50)
        print("Seeding completed successfully!")
        print("="*50)
        
    except Exception as e:
        print(f"\nError during seeding: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()