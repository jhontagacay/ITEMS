from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.itmonitoringsystem, name='load_base'),
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/add/', views.equipment_add, name='equipment_add'),
    path('equipment/<int:pk>/edit/',views.equipment_edit, name='equipment_edit'),
    path('equipment/<int:pk>/delete/',views.equipment_delete, name='equipment_delete'),
    path('borrow/',views.borrow_create, name='borrow_create'),
    path('borrow/<int:pk>/return/',views.borrow_return, name='borrow_return'),
    path('transactions/',views.transaction_list, name='transaction_list'),
    path('transactions/<int:pk>/',views.transaction_detail, name='transaction_detail'),
]