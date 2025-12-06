from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public URLs
    path('', views.home, name='home'),
    path('books/', views.book_list, name='book_list'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Member Functions
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    path('return/<int:borrow_id>/', views.return_book, name='return_book'),
    path('reserve/', views.reserve_table, name='reserve_table'),
    path('read/<int:book_id>/', views.start_reading, name='start_reading'),
    path('stop-reading/<int:activity_id>/',
         views.stop_reading, name='stop_reading'),

    # Librarian Functions
    path('librarian/borrows/', views.manage_borrows, name='manage_borrows'),
    path('librarian/reservations/', views.manage_reservations,
         name='manage_reservations'),
    path('add-book/', views.add_book, name='add_book'),
    # Table Management
    path('librarian/add-table/', views.add_table, name='add_table'),
    path('librarian/tables/', views.manage_tables, name='manage_tables'),
    path('librarian/edit-table/<int:table_id>/',
         views.edit_table, name='edit_table'),
    path('librarian/delete-table/<int:table_id>/',
         views.delete_table, name='delete_table'),

    # API
    path('api/available-tables/', views.get_available_tables,
         name='available_tables'),
]
