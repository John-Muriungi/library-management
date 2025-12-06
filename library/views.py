from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import login, authenticate
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q, Count
from .models import *
from .forms import *
from django.http import JsonResponse

# Permission check functions


def is_librarian(user):
    return user.groups.filter(name='Librarian').exists()


def is_admin(user):
    return user.is_superuser or user.is_staff


def is_member(user):
    return user.groups.filter(name='Member').exists()

# Public Views


def home(request):
    books = Book.objects.filter(available_copies__gt=0)[:6]
    context = {'books': books}
    return render(request, 'home.html', context)


def book_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')

    books = Book.objects.all()

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(isbn__icontains=query)
        )

    if category:
        books = books.filter(category=category)

    categories = Book.objects.values_list('category', flat=True).distinct()
    context = {
        'books': books,
        'categories': categories,
        'query': query,
        'selected_category': category
    }
    return render(request, 'book_list.html', context)


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    is_available = book.available_copies > 0
    context = {
        'book': book,
        'is_available': is_available
    }
    return render(request, 'book_detail.html', context)

# Authentication Views


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Add user to Member group by default
            member_group, created = Group.objects.get_or_create(name='Member')
            user.groups.add(member_group)
            messages.success(
                request, 'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')

# Dashboard Views


@login_required
def dashboard(request):
    user = request.user

    if is_admin(user):
        return admin_dashboard(request)
    elif is_librarian(user):
        return librarian_dashboard(request)
    else:
        return member_dashboard(request)


def member_dashboard(request):
    user = request.user
    borrowed_books = BorrowRecord.objects.filter(user=user, status='Borrowed')
    reservations = Reservation.objects.filter(
        user=user, status__in=['Pending', 'Confirmed'])

    context = {
        'borrowed_books': borrowed_books,
        'reservations': reservations,
        'user': user
    }
    return render(request, 'member_dashboard.html', context)


@login_required
@user_passes_test(is_librarian)
def librarian_dashboard(request):
    # Statistics
    total_books = Book.objects.count()
    total_members = User.objects.filter(groups__name='Member').count()
    borrowed_count = BorrowRecord.objects.filter(status='Borrowed').count()
    overdue_count = BorrowRecord.objects.filter(
        status='Borrowed',
        due_date__lt=timezone.now()
    ).count()

    # Recent activities
    recent_borrows = BorrowRecord.objects.filter(
        status='Borrowed'
    ).order_by('-borrow_date')[:10]

    pending_reservations = Reservation.objects.filter(
        status='Pending'
    )[:5]

    context = {
        'total_books': total_books,
        'total_members': total_members,
        'borrowed_count': borrowed_count,
        'overdue_count': overdue_count,
        'recent_borrows': recent_borrows,
        'pending_reservations': pending_reservations
    }
    return render(request, 'librarian_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Admin statistics
    total_users = User.objects.count()
    active_borrows = BorrowRecord.objects.filter(status='Borrowed').count()
    available_tables = Table.objects.filter(status='Available').count()

    # Most popular books
    popular_books = Book.objects.annotate(
        borrow_count=Count('borrow_records')
    ).order_by('-borrow_count')[:5]

    # Recent user activities
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Reading activities
    reading_now = ReadingActivity.objects.filter(
        end_time__isnull=True
    ).select_related('user', 'book')[:10]

    context = {
        'total_users': total_users,
        'active_borrows': active_borrows,
        'available_tables': available_tables,
        'popular_books': popular_books,
        'recent_users': recent_users,
        'reading_now': reading_now
    }
    return render(request, 'admin_dashboard.html', context)

# Book Management


@login_required
def borrow_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if book.available_copies <= 0:
        messages.error(request, 'This book is not available for borrowing.')
        return redirect('book_detail', book_id=book_id)

    # Check if user already borrowed this book
    existing_borrow = BorrowRecord.objects.filter(
        user=request.user,
        book=book,
        status='Borrowed'
    ).exists()

    if existing_borrow:
        messages.warning(request, 'You have already borrowed this book.')
        return redirect('book_detail', book_id=book_id)

    if request.method == 'POST':
        borrow_record = BorrowRecord(
            user=request.user,
            book=book,
            due_date=timezone.now() + timedelta(days=14)
        )
        borrow_record.save()

        # Update available copies
        book.available_copies -= 1
        book.save()

        messages.success(request, f'Successfully borrowed "{book.title}"')
        return redirect('dashboard')

    context = {'book': book}
    return render(request, 'borrow_book.html', context)


@login_required
def return_book(request, borrow_id):
    borrow_record = get_object_or_404(
        BorrowRecord, id=borrow_id, user=request.user)

    if request.method == 'POST':
        borrow_record.return_date = timezone.now()
        borrow_record.status = 'Returned'

        # Calculate fine if overdue
        if borrow_record.is_overdue():
            borrow_record.fine_amount = borrow_record.calculate_fine()

        borrow_record.save()

        # Update available copies
        book = borrow_record.book
        book.available_copies += 1
        book.save()

        messages.success(
            request, f'Successfully returned "{borrow_record.book.title}"')
        return redirect('dashboard')

    context = {'borrow_record': borrow_record}
    return render(request, 'return_book.html', context)

# Table Reservation


@login_required
def reserve_table(request):
    # Get all available tables
    tables = Table.objects.filter(status='Available')

    if request.method == 'POST':
        # Get form data
        reservation_date = request.POST.get('reservation_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        purpose = request.POST.get('purpose', '')
        table_id = request.POST.get('table')

        # Basic validation
        if not all([reservation_date, start_time, end_time, table_id]):
            messages.error(request, 'All fields are required.')
            context = {'tables': tables}
            return render(request, 'reserve_table.html', context)

        try:
            table = Table.objects.get(id=table_id)

            # Create reservation
            reservation = Reservation(
                user=request.user,
                table=table,
                reservation_date=reservation_date,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
                status='Pending'
            )
            reservation.save()

            messages.success(
                request, f'Reservation submitted for Table {table.table_number}!')
            return redirect('dashboard')

        except Table.DoesNotExist:
            messages.error(request, 'Selected table does not exist.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    context = {'tables': tables}
    return render(request, 'reserve_table.html', context)

# Librarian Functions


@login_required
@user_passes_test(is_librarian)
def manage_borrows(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')

    # Start with all borrows
    borrows = BorrowRecord.objects.all().select_related(
        'user', 'book').order_by('-borrow_date')

    # Apply filters
    if status_filter:
        borrows = borrows.filter(status=status_filter)

    if search_query:
        borrows = borrows.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(book__title__icontains=search_query) |
            Q(book__author__icontains=search_query)
        )

    # Handle POST actions
    if request.method == 'POST':
        borrow_id = request.POST.get('borrow_id')
        action = request.POST.get('action')

        borrow = get_object_or_404(BorrowRecord, id=borrow_id)

        if action == 'return':
            borrow.return_date = timezone.now()
            borrow.status = 'Returned'

            # Calculate fine if overdue
            if borrow.is_overdue():
                days_overdue = (timezone.now() - borrow.due_date).days
                borrow.fine_amount = days_overdue * 5  # $5 per day

            borrow.save()

            # Update available copies
            book = borrow.book
            book.available_copies += 1
            book.save()

            messages.success(
                request, f'Book "{borrow.book.title}" marked as returned.')

        elif action == 'extend':
            new_due_date = request.POST.get('new_due_date')
            if new_due_date:
                borrow.due_date = new_due_date
                borrow.save()
                messages.success(
                    request, f'Due date extended for "{borrow.book.title}".')

    # Calculate statistics
    from datetime import timedelta

    active_borrows = BorrowRecord.objects.filter(status='Borrowed').count()
    overdue_books = BorrowRecord.objects.filter(
        status='Borrowed',
        due_date__lt=timezone.now()
    ).count()

    today = timezone.now().date()
    returned_today = BorrowRecord.objects.filter(
        return_date__date=today,
        status='Returned'
    ).count()

    total_records = borrows.count()

    # Get overdue list for sidebar
    overdue_list = BorrowRecord.objects.filter(
        status='Borrowed',
        due_date__lt=timezone.now()
    ).select_related('user', 'book')[:5]

    # Calculate days overdue for each
    for borrow in overdue_list:
        borrow.days_overdue = (timezone.now() - borrow.due_date).days

    # Get recent returns
    recent_returns = BorrowRecord.objects.filter(
        status='Returned'
    ).order_by('-return_date')[:5]

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(borrows, 20)  # 20 items per page

    try:
        borrows_paginated = paginator.page(page)
    except PageNotAnInteger:
        borrows_paginated = paginator.page(1)
    except EmptyPage:
        borrows_paginated = paginator.page(paginator.num_pages)

    context = {
        'borrows': borrows_paginated,
        'active_borrows': active_borrows,
        'overdue_books': overdue_books,
        'returned_today': returned_today,
        'total_records': total_records,
        'overdue_list': overdue_list,
        'recent_returns': recent_returns,
    }

    return render(request, 'manage_borrows.html', context)


@login_required
@user_passes_test(is_librarian)
def manage_reservations(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('search', '')

    # Start with all reservations
    reservations = Reservation.objects.all().select_related(
        'user', 'table').order_by('-created_at')

    # Apply filters
    if status_filter:
        reservations = reservations.filter(status=status_filter)

    if date_filter:
        reservations = reservations.filter(reservation_date=date_filter)

    if search_query:
        reservations = reservations.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(table__table_number__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )

    # Handle POST actions
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        action = request.POST.get('action')

        reservation = get_object_or_404(Reservation, id=reservation_id)

        if action == 'confirm':
            reservation.status = 'Confirmed'
            reservation.table.status = 'Reserved'
            reservation.table.save()
            messages.success(
                request, f'Reservation confirmed for Table {reservation.table.table_number}.')

        elif action == 'cancel':
            reservation.status = 'Cancelled'
            reservation.table.status = 'Available'
            reservation.table.save()
            messages.success(request, f'Reservation cancelled.')

        elif action == 'complete':
            reservation.status = 'Completed'
            reservation.table.status = 'Available'
            reservation.table.save()
            messages.success(request, f'Reservation marked as completed.')

        reservation.save()

    # Calculate statistics
    from datetime import date

    pending_count = Reservation.objects.filter(status='Pending').count()
    confirmed_count = Reservation.objects.filter(status='Confirmed').count()

    # Use timezone-aware today for comparisons
    today = timezone.now().date()
    today_count = Reservation.objects.filter(reservation_date=today).count()
    total_count = reservations.count()

    # Get today's reservations
    todays_reservations = Reservation.objects.filter(
        reservation_date=today
    ).order_by('start_time')[:10]

    # Calculate duration for each reservation (FIXED: Use timezone-aware datetime)
    for reservation in reservations:
        # Combine date and time, making them timezone-aware
        reservation_datetime = timezone.make_aware(
            timezone.datetime.combine(
                reservation.reservation_date, reservation.start_time)
        )
        reservation_end = timezone.make_aware(
            timezone.datetime.combine(
                reservation.reservation_date, reservation.end_time)
        )

        # Calculate duration
        duration = reservation_end - reservation_datetime
        reservation.duration_hours = duration.seconds // 3600
        reservation.duration_minutes = (duration.seconds % 3600) // 60

        # Check if reservation is active now (FIXED: Use timezone.now())
        now = timezone.now()
        reservation.is_active = reservation_datetime <= now <= reservation_end
        reservation.is_upcoming = reservation_datetime > now

    # Most active user
    from django.db.models import Count
    most_active = User.objects.annotate(
        reservation_count=Count('reservations')
    ).order_by('-reservation_count').first()
    most_active_user = most_active.username if most_active else None
    most_active_user_count = most_active.reservation_count if most_active else 0

    # Most popular table
    popular_table_obj = Table.objects.annotate(
        reservation_count=Count('reservations')
    ).order_by('-reservation_count').first()
    popular_table = f"Table {popular_table_obj.table_number}" if popular_table_obj else None
    popular_table_count = popular_table_obj.reservation_count if popular_table_obj else 0

    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    page = request.GET.get('page', 1)
    paginator = Paginator(reservations, 15)  # 15 items per page

    try:
        reservations_paginated = paginator.page(page)
    except PageNotAnInteger:
        reservations_paginated = paginator.page(1)
    except EmptyPage:
        reservations_paginated = paginator.page(paginator.num_pages)

    context = {
        'reservations': reservations_paginated,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'today_count': today_count,
        'total_count': total_count,
        'todays_reservations': todays_reservations,
        'most_active_user': most_active_user,
        'most_active_user_count': most_active_user_count,
        'popular_table': popular_table,
        'popular_table_count': popular_table_count,
    }

    return render(request, 'manage_reservations.html', context)


@login_required
@user_passes_test(is_librarian)
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Book added successfully!')
            return redirect('book_list')
    else:
        form = BookForm()

    context = {'form': form}
    return render(request, 'add_book.html', context)

# Reading Activity


@login_required
def start_reading(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # End any existing reading activity
    ReadingActivity.objects.filter(user=request.user, end_time__isnull=True).update(
        end_time=timezone.now()
    )

    # Start new reading activity
    activity = ReadingActivity.objects.create(
        user=request.user,
        book=book
    )

    messages.success(request, f'Started reading "{book.title}"')
    return redirect('book_detail', book_id=book_id)


@login_required
def stop_reading(request, activity_id):
    activity = get_object_or_404(
        ReadingActivity, id=activity_id, user=request.user)
    activity.end_time = timezone.now()
    activity.save()

    messages.success(request, 'Reading session ended.')
    return redirect('dashboard')

# API Endpoints for AJAX


@login_required
def get_available_tables(request):
    date = request.GET.get('date')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')

    if date and start_time and end_time:
        # Convert string to datetime objects
        reservation_date = datetime.strptime(date, '%Y-%m-%d').date()
        start_dt = datetime.strptime(start_time, '%H:%M').time()
        end_dt = datetime.strptime(end_time, '%H:%M').time()

        # Find tables that are not reserved for this time slot
        reserved_tables = Reservation.objects.filter(
            reservation_date=reservation_date,
            start_time__lt=end_dt,
            end_time__gt=start_dt,
            status__in=['Pending', 'Confirmed']
        ).values_list('table_id', flat=True)

        available_tables = Table.objects.filter(
            status='Available'
        ).exclude(id__in=reserved_tables)

        data = [{'id': t.id, 'number': t.table_number, 'capacity': t.capacity}
                for t in available_tables]
        return JsonResponse(data, safe=False)

    return JsonResponse([], safe=False)

# added this


# Table Management Views
@login_required
@user_passes_test(is_librarian)
def add_table(request):
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save()
            messages.success(
                request, f'Table {table.table_number} added successfully!')
            return redirect('manage_tables')
    else:
        form = TableForm()

    context = {'form': form}
    return render(request, 'add_table.html', context)


@login_required
@user_passes_test(is_librarian)
def edit_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    if request.method == 'POST':
        form = TableForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'Table {table.table_number} updated successfully!')
            return redirect('manage_tables')
    else:
        form = TableForm(instance=table)

    context = {'form': form, 'table': table}
    return render(request, 'edit_table.html', context)


@login_required
@user_passes_test(is_librarian)
def delete_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    if request.method == 'POST':
        table_number = table.table_number
        table.delete()
        messages.success(
            request, f'Table {table_number} deleted successfully!')
        return redirect('manage_tables')

    context = {'table': table}
    return render(request, 'delete_table.html', context)


@login_required
@user_passes_test(is_librarian)
def manage_tables(request):
    tables = Table.objects.all().order_by('table_number')

    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        tables = tables.filter(status=status_filter)

    # Search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        tables = tables.filter(
            Q(table_number__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Statistics
    total_tables = tables.count()
    available_tables = tables.filter(status='Available').count()
    reserved_tables = tables.filter(status='Reserved').count()
    occupied_tables = tables.filter(status='Occupied').count()

    context = {
        'tables': tables,
        'total_tables': total_tables,
        'available_tables': available_tables,
        'reserved_tables': reserved_tables,
        'occupied_tables': occupied_tables,
        'status_filter': status_filter,
        'search_query': search_query,
    }

    return render(request, 'manage_tables.html', context)


@login_required
def view_profile(request):
    user = request.user
    return render(request, 'view_profile.html', {'user': user})
