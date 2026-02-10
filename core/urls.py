from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [   
     path('',dashboard ,name='dashboard'),

    path('dashboard/',dashboard ,name='dashboard'),
    path('updates/stream/', updates_stream, name='updates_stream'),
    path('products/',products ,name='products'),
    path('products/<int:product_id>/edit/', product_edit, name='product_edit'),
    path('lots/',lots ,name='lots'),
    path('movements/',movements ,name='movements'),
    path('alerts/',alerts ,name='alerts'),
    path('historique/',historique ,name='historique'),
    path('famille/',famille ,name='famille'),

]
