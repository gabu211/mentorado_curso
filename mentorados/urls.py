from django.urls import path
from . import views
urlpatterns = [
 path('', views.mentorados, name='mentorados'),
 path('reunioes/', views.reunioes, name='reunioes'),
 path('auth/', views.auth, name="auth_mentorado"),

]
