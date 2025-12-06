from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta


class Book(models.Model):
    CATEGORY_CHOICES = [
        ('Fiction', 'Fiction'),
        ('Non-Fiction', 'Non-Fiction'),
        ('Science', 'Science'),
        ('Technology', 'Technology'),
        ('History', 'History'),
        ('Biography', 'Biography'),
        ('Children', 'Children'),
        ('Other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    total_copies = models.IntegerField(default=1)
    available_copies = models.IntegerField(default=1)
    cover_image = models.ImageField(
        upload_to='book_covers/', blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.author}"

    def save(self, *args, **kwargs):
        if not self.available_copies:
            self.available_copies = self.total_copies
        super().save(*args, **kwargs)


# Table Model
class Table(models.Model):
    TABLE_STATUS = [
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Reserved', 'Reserved'),
        ('Maintenance', 'Maintenance'),
    ]

    table_number = models.CharField(max_length=10, unique=True)
    capacity = models.IntegerField(default=4)
    location = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=TABLE_STATUS, default='Available')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True)  # Make sure this exists
    updated_at = models.DateTimeField(
        auto_now=True)      # Make sure this exists

    def __str__(self):
        return f"Table {self.table_number}"

    def is_available(self):
        return self.status == 'Available'

    def get_reservations_today(self):
        from datetime import date
        return self.reservations.filter(reservation_date=date.today())


class BorrowRecord(models.Model):
    BORROW_STATUS = [
        ('Borrowed', 'Borrowed'),
        ('Returned', 'Returned'),
        ('Overdue', 'Overdue'),
        ('Lost', 'Lost'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='borrowed_books')
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name='borrow_records')
    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=BORROW_STATUS, default='Borrowed')
    fine_amount = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    def is_overdue(self):
        if self.status == 'Borrowed' and timezone.now() > self.due_date:
            return True
        return False

    def calculate_fine(self):
        if self.is_overdue() and self.status == 'Borrowed':
            days_overdue = (timezone.now() - self.due_date).days
            return days_overdue * 5  # $5 per day
        return 0


class Reservation(models.Model):
    RESERVATION_STATUS = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reservations')
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=20, choices=RESERVATION_STATUS, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - Table {self.table.table_number}"


class ReadingActivity(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reading_activities')
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name='reading_activities')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    pages_read = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} reading {self.book.title}"
