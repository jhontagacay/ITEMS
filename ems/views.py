from django.shortcuts import render, redirect, get_object_or_404
from .models import ITMonitoringSystem
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from .models import Equipment, BorrowTransaction, Department
from .forms import BorrowForm, ReturnForm, EquipmentForm, TransactionFilterForm

def itmonitoringsystem(request):
    return render(request, 'ems/base.html')

def dashboard(request):
    equipments = Equipment.objects.all()
    total_equipment = equipments.count()
    available = equipments.filter(status='available').count()
    borrowed = equipments.filter(status='borrowed').count()
    unavailable = equipments.filter(status='unavailable').count()

    ongoing_txns = (BorrowTransaction.objects
        .filter(status='ongoing')
        .select_related('equipment', 'department')
        .order_by('expected_return'))

    overdue = [t for t in ongoing_txns if t.is_overdue]

    recent_txns = (BorrowTransaction.objects
        .select_related('equipment', 'department')
        .order_by('-date_borrowed')[:8])

    dept_stats = (BorrowTransaction.objects
        .filter(status='ongoing')
        .values('department__name')
        .annotate(count=Count('id'))
        .order_by('-count'))

    return render(request, 'ems/dashboard.html', {
        'total_equipment': total_equipment, 
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
        qs = qs.filter(Q(name__icontains=q) | Q(serial_number__icontains=q) | Q(category__icontains=q))
    if status_f:
        qs = qs.filter(status=status_f)
    return render(request, 'ems/all_equipment.html', {'equipments': qs, 'q': q, 'status_f': status_f})

def equipment_add(request):
    form = EquipmentForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Equipment added successfully.')
        return redirect('all_equipment')
    return render(request, 'ems/equipment_form.html', {'form': form, 'title': 'Add Equipment'})

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

def borrow_create(request):
    form = BorrowForm(request.POST or None)
    if form.is_valid():
        txn = form.save(commit=False)
        txn.save()
        txn.equipment.status = 'borrowed'
        txn.equipment.save()
        messages.success(request, f'Equipment "{txn.equipment.name}" borrowed by {txn.borrower_name}.')
        return redirect('dashboard')
    return render(request, 'ems/borrow.html', {'form': form})

def borrow_return(request, pk):
    txn  = get_object_or_404(BorrowTransaction, pk=pk, status='ongoing')
    form = ReturnForm(request.POST or None)
    if form.is_valid():
        txn.mark_returned(
            returned_by=form.cleaned_data['returned_by'],
            received_by=form.cleaned_data['received_by'],
            notes=form.cleaned_data['return_notes'],
        )
        messages.success(request, f'"{txn.equipment.name}" has been returned and marked available.')
        return redirect('history_logs')
    return render(request, 'ems/return.html', {'form': form, 'txn': txn})

def transaction_detail(request, pk):
    txn = get_object_or_404(BorrowTransaction.objects.select_related('equipment', 'department'), pk=pk)
    return render(request, 'ems/transaction_detail.html', {'txn': txn})

def history_logs(request):
    form = TransactionFilterForm(request.GET or None)
    qs   = BorrowTransaction.objects.select_related('equipment', 'department')
    if form.is_valid():
        d = form.cleaned_data
        if d.get('search'):
            s = d['search']
            qs = qs.filter(Q(borrower_name__icontains=s) | Q(equipment__name__icontains=s))
        if d.get('department'):
            qs = qs.filter(department=d['department'])
        if d.get('status'):
            qs = qs.filter(status=d['status'])
        if d.get('date_from'):
            qs = qs.filter(date_borrowed__date__gte=d['date_from'])
        if d.get('date_to'):
            qs = qs.filter(date_borrowed__date__lte=d['date_to'])
        sort = d.get('sort') or '-date_borrowed'
        qs = qs.order_by(sort)
    else:
        qs = qs.order_by('-date_borrowed')

    return render(request, 'ems/history_logs.html', {'form': form, 'transactions': qs})

def transaction_edit(request, pk):
    transaction = get_object_or_404(BorrowTransaction, pk=pk)
    if request.method == 'POST':
        transaction.borrower_name = request.POST.get('borrower_name')
        equipment_id = request.POST.get('equipment')
        if equipment_id:
            transaction.equipment = get_object_or_404(Equipment, id=equipment_id)
            
        dept_id = request.POST.get('department')
        if dept_id:
            transaction.department = get_object_or_404(Department, id=dept_id)
    
        new_date = request.POST.get('date_borrowed')
        if new_date:
            transaction.date_borrowed = new_date
            
        transaction.save()
        return redirect('history_logs')
    
    context = {
        'transaction': transaction,
        'equipments': Equipment.objects.all(),
        'departments': Department.objects.all(),
    }
    return render(request, 'ems/transaction_form.html', context)
    
def transaction_delete(request, pk):
    if request.method == 'POST':
        transaction = get_object_or_404(BorrowTransaction, pk=pk)
        transaction.equipment.status = 'available'
        transaction.equipment.save()
        transaction.delete()
    return redirect('dashboard')