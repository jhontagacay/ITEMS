from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('', views.dashboard, name='dashboard'), 
    path('equipment/', views.all_equipment, name='all_equipment'),
    path('equipment/add/', views.equipment_add, name='equipment_add'),
    path('equipment/edit/<int:pk>/', views.equipment_edit, name='equipment_edit'),
    path('equipment/delete/<int:pk>/', views.equipment_delete, name='equipment_delete'),
    path('borrow/', views.borrow_create, name='borrow_create'),
    path('return/<int:pk>/', views.borrow_return, name='borrow_return'),
    path('history/', views.history_logs, name='history_logs'),
    path('history/detail/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('history/edit/<int:pk>/', views.transaction_edit, name='transaction_edit'),
    path('history/delete/<int:pk>/', views.transaction_delete, name='transaction_delete'),
    path('division/add/', views.division_add, name='division_add'),
    path('monthly_record/', views.monthly_record, name='monthly_record'),
    path('monthly_record/export/', views.monthly_record_export, name='monthly_record_export'),
    path('signup/', views.signup, name='signup_view'),
    path('password-reset/', views.password_reset, name='password_reset_view'),
    path('transaction/<int:pk>/return/', views.borrow_return, name='borrow_return'),
]