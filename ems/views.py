from django.shortcuts import render, redirect, get_object_or_404
from .models import ITMonitoringSystem
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from .models import Equipment, BorrowTransaction, Division
from .forms import BorrowForm, ReturnForm, EquipmentForm, TransactionFilterForm, DivisionForm
from datetime import datetime

def itmonitoringsystem(request):
    return render(request, 'ems/base.html')

def dashboard(request):
    equipments = Equipment.objects.all()
    total = equipments.count()
    available = equipments.filter(status='available').count()
    borrowed = equipments.filter(status='borrowed').count()
    unavailable = equipments.filter(status='unavailable').count()

    ongoing_txns = (BorrowTransaction.objects
        .filter(status='ongoing')
        .select_related('equipment', 'division')
        .order_by('due_date'))

    overdue = [t for t in ongoing_txns if t.is_overdue]

    recent_txns  = (BorrowTransaction.objects
        .select_related('equipment', 'division')
        .order_by('-created_at')[:8])

    dept_stats = (BorrowTransaction.objects
        .filter(status='ongoing')
        .values('division__name')
        .annotate(count=Count('id'))
        .order_by('-count'))

    return render(request, 'ems/dashboard.html', {
        'total': total, 
        'available': available,
        'borrowed': borrowed, 
        'unavailable': unavailable,
        'ongoing_txns': ongoing_txns,
        'recent_txns': recent_txns,
        'overdue': overdue,
        'dept_stats': dept_stats,
    })

def all_equipment(request):
    qs = Equipment.objects.all()
    q  = request.GET.get('q', '')
    status_f = request.GET.get('status', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(serial_number__icontains=q))
    if status_f:
        qs = qs.filter(status=status_f)
    return render(request, 'ems/all_equipment.html', {'equipments': qs, 'q': q, 'status_f': status_f})

def equipment_add(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipment added successfully.')
            return redirect('borrow_create')
    return redirect('borrow_create')

def equipment_edit(request, pk):
    eq   = get_object_or_404(Equipment, pk=pk)
    form = EquipmentForm(request.POST or None, instance=eq)
    if form.is_valid():
        form.save()
        messages.success(request, 'Equipment updated.')
        return redirect('all_equipment')
    return render(request, 'ems/equipment_form.html', {'form': form, 'title': 'Edit Equipment'})

def equipment_delete(request, pk):
    eq = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        eq.delete()
        messages.success(request, 'Equipment deleted.')
        return redirect('all_equipment')
    return render(request, 'ems/confirm_delete.html', {'obj': eq, 'type': 'Equipment'})

def division_add(request):
    if request.method == 'POST':
        form = DivisionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Division added successfully!")
            return redirect('borrow_create')
    return redirect('borrow_create')

def borrow_create(request):
    if request.method == 'POST':
        form = BorrowForm(request.POST)
        if form.is_valid():
            txn = form.save(commit=False)
            day = form.cleaned_data['due_date_day']
            time = form.cleaned_data['due_date_time']
            txn.due_date = datetime.combine(day, time)
            txn.save()
        
            txn.equipment.status = 'borrowed'
            txn.equipment.save()
            
            messages.success(request, 'Transaction recorded successfully.')
            return redirect('dashboard')

    else:
        form = BorrowForm()

    context = {
        'form': form,
        'equipment_form': EquipmentForm(),
        'division_form': DivisionForm(),
    }
    
    return render(request, 'ems/borrow.html', context)

def borrow_return(request, pk):
    txn  = get_object_or_404(BorrowTransaction, pk=pk, status='ongoing')
    form = ReturnForm(request.POST or None)
    if form.is_valid():
        txn.mark_returned(
            returned_by=form.cleaned_data['returned_by'],
            received_by=form.cleaned_data['received_by'],
            notes=form.cleaned_data['return_notes'],
        )
        messages.success(request, f'"{txn.equipment.name}" has been returned.')
        return redirect('history_logs')
    return render(request, 'ems/return.html', {'form': form, 'txn': txn})

def history_logs(request):
    form = TransactionFilterForm(request.GET or None)
    qs   = BorrowTransaction.objects.select_related('equipment', 'division')
    if form.is_valid():
        d = form.cleaned_data
        if d.get('search'):
            s = d['search']
            qs = qs.filter(Q(borrower_name__icontains=s) | Q(equipment__name__icontains=s))
        if d.get('division'):
            qs = qs.filter(division=d['division'])
        if d.get('status'):
            qs = qs.filter(status=d['status'])
        if d.get('date_from'):
            qs = qs.filter(date_borrowed__date__gte=d['date_from'])
        if d.get('date_to'):
            qs = qs.filter(date_borrowed__date__lte=d['date_to'])
        sort = d.get('sort') or '-date_borrowed'
        qs = qs.order_by(sort)
    qs = qs.order_by('-date_borrowed')
    return render(request, 'ems/history_logs.html', {'form': form, 'transactions': qs})

def transaction_detail(request, pk):
    txn = get_object_or_404(BorrowTransaction.objects.select_related('equipment', 'division'), pk=pk)
    return render(request, 'ems/transaction_detail.html', {'txn': txn})

def transaction_edit(request, pk):
    transaction = get_object_or_404(BorrowTransaction, pk=pk)
    if request.method == 'POST':
        transaction.borrower_name = request.POST.get('borrower_name')
        equipment_id = request.POST.get('equipment')
        if equipment_id:
            transaction.equipment = get_object_or_404(Equipment, id=equipment_id)

        div_id = request.POST.get('division')
        if div_id:
            transaction.division = get_object_or_404(Division, id=div_id)

        new_date = request.POST.get('date_borrowed')
        if new_date:
            transaction.date_borrowed = new_date

        transaction.save()
        messages.success(request, 'Transaction updated.')
        return redirect('history_logs')
    
    context = {
        'transaction': transaction,
        'equipments': Equipment.objects.all(),
        'division': Division.objects.all(),
    }
    return render(request, 'ems/transaction_form.html', context)

def transaction_delete(request, pk):
    if request.method == 'POST':
        transaction = get_object_or_404(BorrowTransaction, pk=pk)
        if transaction.status == 'ongoing':
            transaction.equipment.status = 'available'
            transaction.equipment.save()
        transaction.delete()
        messages.success(request, 'Transaction deleted.')
    return redirect('dashboard')