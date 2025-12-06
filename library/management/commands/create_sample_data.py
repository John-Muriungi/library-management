from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from library.models import Book, Table, BorrowRecord, Reservation
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Creates sample data for testing'

    def handle(self, *args, **kwargs):
        # Create groups if they don't exist
        groups = ['Member', 'Librarian']
        for group_name in groups:
            Group.objects.get_or_create(name=group_name)

        # Create librarian user
        librarian, created = User.objects.get_or_create(
            username='librarian',
            defaults={
                'email': 'librarian@library.com',
                'first_name': 'Library',
                'last_name': 'Manager'
            }
        )
        librarian.set_password('librarian123')
        librarian.save()

        # Add librarian to Librarian group
        librarian_group = Group.objects.get(name='Librarian')
        librarian.groups.add(librarian_group)

        # Create member users
        for i in range(1, 6):
            member, created = User.objects.get_or_create(
                username=f'member{i}',
                defaults={
                    'email': f'member{i}@library.com',
                    'first_name': f'Member{i}',
                    'last_name': 'User'
                }
            )
            member.set_password('password123')
            member.save()

            # Add member to Member group
            member_group = Group.objects.get(name='Member')
            member.groups.add(member_group)

        self.stdout.write(self.style.SUCCESS(
            'Sample users created successfully'))
