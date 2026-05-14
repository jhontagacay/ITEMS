from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import ITMonitoringSystem, Equipment, BorrowTransaction, Division
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from .forms import BorrowForm, ReturnForm, EquipmentForm, TransactionFilterForm, DivisionForm, YourSignupForm
from datetime import datetime 
import csv
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Attempting login for: {username}")
        user = authenticate(request, username=username, password=password)
        print(f"Authentication result: {user}")
        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'ems/login.html')

def user_logout(request):
    if request.method in ['GET', 'POST']:
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('user_login')

@login_required(login_url='user_login')
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

    recent_txns = (BorrowTransaction.objects
        .select_related('equipment', 'division')
        .order_by('-created_at')[:8])

    dept_stats = (BorrowTransaction.objects
        .filter(status='ongoing')
        .values('division__name')
        .annotate(count=Count('id'))
        .order_by('-count'))

    division_stats = []
    for division in Division.objects.annotate(
        count=Count('borrowtransaction', filter=Q(borrowtransaction__status='ongoing'))
    ).order_by('-count', 'name'):
        percent = 0
        if borrowed:
            percent = round((division.count / borrowed) * 100)
        division_stats.append({
            'name': division.name or 'General',
            'count': division.count,
            'percent': percent,
        })
        
    return render(request, 'ems/dashboard.html', {
        'total': total, 
        'available': available,
        'borrowed': borrowed, 
        'unavailable': unavailable,
        'ongoing_txns': ongoing_txns,
        'recent_txns': recent_txns,
        'overdue': overdue,
        'dept_stats': dept_stats,
        'division_stats': division_stats,
    })

def all_equipment(request):
    qs = Equipment.objects.all()
    q = request.GET.get('q', '')
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

def equipment_edit(request, pk):
    eq = get_object_or_404(Equipment, pk=pk)
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
            obj = form.save()
            messages.success(request, f"Division '{obj.name}' added successfully!")
            # This ensures the user stays on the Edit page or Borrow page they were on
            return redirect(request.META.get('HTTP_REFERER', 'history_logs'))
    return redirect('history_logs')

def borrow_create(request):
    initial = {}
    equipment_id = request.GET.get('equipment')
    if equipment_id:
        try:
            equipment = Equipment.objects.get(pk=equipment_id, status='available')
        except Equipment.DoesNotExist:
            equipment = None
        else:
            initial['equipment'] = equipment

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
        form = BorrowForm(initial=initial)

    context = {
        'form': form,
        'equipment_form': EquipmentForm(),
        'division_form': DivisionForm(),
    }
    return render(request, 'ems/borrow.html', context)

def borrow_return(request, pk):
    txn = get_object_or_404(BorrowTransaction, pk=pk, status='ongoing')
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
    qs = BorrowTransaction.objects.select_related('equipment', 'division')

    if form.is_valid():
        d = form.cleaned_data
    
        if d.get('search'):
            qs = qs.filter(
                Q(borrower_name__icontains=d['search']) | 
                Q(equipment__name__icontains=d['search'])
            )
            
        if d.get('division'):
            qs = qs.filter(division=d['division'])    
        if d.get('status'):
            qs = qs.filter(status=d['status'])
        if d.get('date_from'):
            qs = qs.filter(date_borrowed__date__gte=d['date_from'])
        if d.get('date_to'):
            qs = qs.filter(date_borrowed__date__lte=d['date_to'])
            
        sort_by = d.get('sort') or '-date_borrowed'
        qs = qs.order_by(sort_by)
    else:
        qs = qs.order_by('-date_borrowed')

    return render(request, 'ems/history_logs.html', {
        'form': form, 
        'transactions': qs
    })
    
def transaction_detail(request, pk):
    txn = get_object_or_404(
        BorrowTransaction.objects.select_related('equipment', 'division'), 
        pk=pk
    )
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

        new_borrow_date = request.POST.get('date_borrowed')
        if new_borrow_date:
            transaction.date_borrowed = new_borrow_date
            
        new_return_date = request.POST.get('date_returned')
        if new_return_date:
            transaction.date_returned = new_return_date
            transaction.status = 'returned'
            transaction.equipment.status = 'available'
            transaction.equipment.save()
        elif 'date_returned' in request.POST and not new_return_date:
            transaction.date_returned = None
            transaction.status = 'ongoing'
            transaction.equipment.status = 'borrowed'
            transaction.equipment.save()

        transaction.save()
        messages.success(request, 'Transaction updated.')
        return redirect('history_logs')
    
    context = {
        'transaction': transaction,
        'equipments': Equipment.objects.all(),
        'divisions': Division.objects.all(),
    }
    return render(request, 'ems/transaction_form.html', context)

def transaction_delete(request, pk):
    transaction = get_object_or_404(BorrowTransaction, pk=pk)
    
    if transaction.status == 'ongoing':
        transaction.equipment.status = 'available'
        transaction.equipment.save()
            
    transaction.delete()
    messages.success(request, 'Transaction deleted.')
    return redirect('history_logs')

def monthly_record(request):
    from django.db.models import Count, Q
    from calendar import month_name
    import datetime

    current_date = timezone.now()
    month = int(request.GET.get('month', current_date.month))
    year = int(request.GET.get('year', current_date.year))

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    month_transactions = BorrowTransaction.objects.filter(
        date_borrowed__date__gte=start_date,
        date_borrowed__date__lt=end_date
    ).select_related('equipment', 'division')

    search_query = request.GET.get('search', '')
    division_filter = request.GET.get('division', '')
    status_filter = request.GET.get('status', '')

    if search_query:
        month_transactions = month_transactions.filter(
            Q(borrower_name__icontains=search_query) |
            Q(equipment__name__icontains=search_query) |
            Q(equipment__serial_number__icontains=search_query)
        )

    if division_filter:
        month_transactions = month_transactions.filter(division__id=division_filter)

    if status_filter:
        month_transactions = month_transactions.filter(status=status_filter)

    total_transactions = month_transactions.count()
    borrow_transactions = month_transactions.count()
    return_transactions = month_transactions.filter(status='returned').count()

    equipment_used = month_transactions.values('equipment').distinct().count()
    total_equipment = Equipment.objects.count()

    division_stats = month_transactions.values('division__name').annotate(
        count=Count('id')
    ).order_by('-count')

    status_stats = month_transactions.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    overdue_count = month_transactions.filter(
        status='ongoing',
        due_date__lt=timezone.now()
    ).count()

    monthly_trend = []
    for i in range(11, -1, -1):
        trend_date = current_date - datetime.timedelta(days=30*i)
        trend_month = trend_date.month
        trend_year = trend_date.year

        trend_start = datetime.date(trend_year, trend_month, 1)
        if trend_month == 12:
            trend_end = datetime.date(trend_year + 1, 1, 1)
        else:
            trend_end = datetime.date(trend_year, trend_month + 1, 1)

        trend_count = BorrowTransaction.objects.filter(
            date_borrowed__date__gte=trend_start,
            date_borrowed__date__lt=trend_end
        ).count()

        monthly_trend.append({
            'month': f"{month_name[trend_month][:3]} {trend_year}",
            'count': trend_count,
            'current': (trend_month == month and trend_year == year)
        })

    months = [(i, month_name[i]) for i in range(1, 13)]
    current_year = timezone.now().year
    years = list(range(current_year - 2, current_year + 3))  # Current year ± 2 years

    context = {
        'month_name': month_name[month],
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'months': months,
        'years': years,
        'total_transactions': total_transactions,
        'borrow_transactions': borrow_transactions,
        'return_transactions': return_transactions,
        'equipment_used': equipment_used,
        'total_equipment': total_equipment,
        'division_stats': division_stats,
        'status_stats': status_stats,
        'overdue_count': overdue_count,
        'monthly_trend': monthly_trend,
        'transactions': month_transactions.order_by('-date_borrowed')[:50],  # Show more transactions
        'search_query': search_query,
        'division_filter': division_filter,
        'status_filter': status_filter,
        'divisions': Division.objects.all(),
    }
    return render(request, 'ems/monthly_record.html', context)


def monthly_record_export(request):
    import datetime

    current_date = timezone.now()
    month = int(request.GET.get('month', current_date.month))
    year = int(request.GET.get('year', current_date.year))

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)

    transactions = BorrowTransaction.objects.filter(
        date_borrowed__date__gte=start_date,
        date_borrowed__date__lt=end_date
    ).select_related('equipment', 'division').order_by('-date_borrowed')

    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(borrower_name__icontains=search_query) |
            Q(equipment__name__icontains=search_query) |
            Q(equipment__serial_number__icontains=search_query)
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="monthly_record_{year}_{month:02d}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transaction #', 'Equipment', 'Serial Number', 'Borrower', 'Division',
        'Date Borrowed', 'Due Date', 'Status', 'Returned Date', 'Returned By', 'Received By'
    ])

    for txn in transactions:
        writer.writerow([
            txn.transaction_number,
            txn.equipment.name,
            txn.equipment.serial_number,
            txn.borrower_name,
            txn.division.name if txn.division else 'General',
            txn.date_borrowed.strftime('%Y-%m-%d %H:%M'),
            txn.due_date.strftime('%Y-%m-%d %H:%M') if txn.due_date else '',
            txn.status.title(),
            txn.date_returned.strftime('%Y-%m-%d %H:%M') if txn.date_returned else '',
            txn.returned_by,
            txn.received_by,
        ])
    return response

def login(request):
    return render(request, 'ems/login.html')

def signup(request):
    if request.method == 'POST':
        form = YourSignupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            email = form.cleaned_data.get('email')
            User.objects.create_user(username=username, password=password, email=email)
            messages.success(request, 'Account created! Please log in.')
            return redirect('user_login')
    else:
        form = YourSignupForm()
        
    return render(request, 'ems/signup.html', {'form': form})

def password_reset(request):
    return render(request, 'ems/password_reset.html')