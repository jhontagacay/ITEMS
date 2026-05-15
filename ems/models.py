from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from datetime import timedelta

class ITMonitoringSystem(models.Model):
    equipment_name = models.CharField(max_length=100)
    
class Division(models.Model):
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
            'available': 'success',
            'borrowed': 'warning',
            'unavailable': 'danger',
        }.get(self.status, 'secondary')


class BorrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('returned', 'Returned'),
    ]

    transaction_number = models.PositiveIntegerField(unique=True, null=True, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='transactions')
    borrower_name = models.CharField(max_length=150)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True)
    purpose = models.TextField()
    released_by = models.CharField(max_length=150)
    date_borrowed = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True) 
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
        if self.status == 'Ongoing' and self.borrowed_date:
            return timezone.now() > self.borrowed_date + timedelta(days=1)
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

@receiver(pre_save, sender=BorrowTransaction)
def assign_transaction_number(sender, instance, **kwargs):
    if instance.transaction_number is None:
        last_transaction = BorrowTransaction.objects.all().order_by('-transaction_number').first()
        if last_transaction and last_transaction.transaction_number:
            instance.transaction_number = last_transaction.transaction_number + 1
        else:
            instance.transaction_number = 1