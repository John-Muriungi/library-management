from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin
from .models import *

# Unregister default User admin
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name',
                    'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'groups', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')


class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category',
                    'total_copies', 'available_copies', 'date_added')
    list_filter = ('category', 'date_added')
    search_fields = ('title', 'author', 'isbn')
    readonly_fields = ('available_copies', 'date_added')
    list_per_page = 20


class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'borrow_date', 'due_date',
                    'return_date', 'status', 'fine_amount')
    list_filter = ('status', 'borrow_date', 'due_date')
    search_fields = ('book__title', 'user__username')
    readonly_fields = ('borrow_date',)
    list_per_page = 20

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('book', 'user')


class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'capacity', 'location', 'status')
    list_filter = ('status', 'location')
    search_fields = ('table_number', 'location')


class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'table', 'reservation_date',
                    'start_time', 'end_time', 'status')
    list_filter = ('status', 'reservation_date')
    search_fields = ('user__username', 'table__table_number')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'table')


class ReadingActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'start_time', 'end_time', 'pages_read')
    list_filter = ('start_time',)
    search_fields = ('user__username', 'book__title')
    readonly_fields = ('start_time',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'book')


# Register models
admin.site.register(Book, BookAdmin)
admin.site.register(Table, TableAdmin)
admin.site.register(BorrowRecord, BorrowRecordAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(ReadingActivity, ReadingActivityAdmin)

# Create custom groups in admin


class CustomGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_user_count')

    def get_user_count(self, obj):
        return obj.user_set.count()
    get_user_count.short_description = 'Number of Users'


admin.site.register(Group, CustomGroupAdmin)

# # Customize admin site headers
# admin.site.site_header = "Library Management Admin"
# admin.site.site_title = "Library Management Admin Portal"
# admin.site.index_title = "Welcome to the Library Management Admin Portal"
# admin.site.empty_value_display = '-empty-'
# admin.site.register(CustomGroupAdmin)
