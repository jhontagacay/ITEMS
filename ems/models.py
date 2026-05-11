from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class ITMonitoringSystem(models.Model):
    equipment_name = models.CharField(max_length=100)
    
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Equipment(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('borrowed',  'Borrowed'),
        ('unavailable', 'Not Available'),
    ]
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    description = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    @property
    def status_badge(self):
        return {
            'available':   'success',
            'borrowed':    'warning',
            'unavailable': 'danger',
        }.get(self.status, 'secondary')

class BorrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('ongoing',   'Ongoing'),
        ('returned',  'Returned'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='transactions')
    borrower_name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    purpose = models.TextField()
    released_by = models.CharField(max_length=150)
    date_borrowed = models.DateTimeField(default=timezone.now)
    expected_return = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')
    date_returned = models.DateTimeField(null=True, blank=True)
    returned_by = models.CharField(max_length=150, blank=True)
    received_by = models.CharField(max_length=150, blank=True)
    return_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_borrowed']

    def __str__(self):
        return f"{self.borrower_name} borrowed {self.equipment.name}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status == 'ongoing' and self.expected_return < timezone.now():
            return True
        return False

    def mark_returned(self, returned_by, received_by, notes=''):
        self.status = 'returned'
        self.date_returned = timezone.now()
        self.returned_by = returned_by
        self.received_by = received_by
        self.return_notes = notes
        self.save()
        self.equipment.status = 'available'
        self.equipment.save()