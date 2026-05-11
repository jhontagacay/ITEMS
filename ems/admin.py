from django.contrib import admin
from .models import ITMonitoringSystem, Equipment, BorrowTransaction, Department

admin.site.register(ITMonitoringSystem)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display  = ['name', 'serial_number', 'category', 'status', 'added_at']
    list_filter   = ['status', 'category']
    search_fields = ['name', 'serial_number']

@admin.register(BorrowTransaction)
class BorrowTransactionAdmin(admin.ModelAdmin):
    list_display  = ['equipment', 'borrower_name', 'department', 'date_borrowed', 'status']
    list_filter   = ['status', 'department']
    search_fields = ['borrower_name', 'equipment__name']
    readonly_fields = ['created_at']
