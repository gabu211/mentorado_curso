from django.shortcuts import render, redirect
from django.http import HttpResponse, request
from .models import Mentorados, Navigators, User, DisponibilidadeHorarios, Reuniao
from django.contrib import messages
from django.contrib.messages import constants
from datetime import datetime, timedelta
from.auth import valida_token
from django.utils import timezone
from django.utils.timezone import make_aware, localtime

def mentorados(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'GET':
        navigators = Navigators.objects.filter(user=request.user)
        mentorados = Mentorados.objects.filter(user=request.user)

        estagio_choices = Mentorados._meta.get_field('estagio').choices  
        estagios_flat = [i[1] for i in estagio_choices]  
        qtd_estagios = [Mentorados.objects.filter(estagio=i[0], user=request.user).count() for i in estagio_choices]

        return render(
            request, 
            'mentorados.html', 
            {
                'estagios': estagio_choices,
                'navigators': navigators,
                'mentorados': mentorados,
                'estagios_flat': estagios_flat,
                'qtd_estagios': qtd_estagios
            }
        )

    elif request.method == 'POST':
        nome = request.POST.get('nome')
        foto = request.FILES.get('foto')
        estagio = request.POST.get("estagio")
        navigator = request.POST.get('navigator')

       
        estagio_valido = [i[0] for i in Mentorados._meta.get_field('estagio').choices]
        if estagio not in estagio_valido:
            estagio = 'E1'  

        
        try:
            navigator = int(navigator)
        except (ValueError, TypeError):
            navigator = None

        mentorado = Mentorados(
            nome=nome,
            foto=foto,
            estagio=estagio,
            navigator_id=navigator if navigator else None,
            user=request.user
        )
        
        mentorado.save()

        messages.add_message(request, constants.SUCCESS, 'Mentorado cadastrado com sucesso!')
        return redirect('mentorados')

def reunioes(request):
    if request.method == 'GET':
        return render(request, 'reunioes.html')
    elif request.method == 'POST':
        data = request.POST.get('data')
        data = datetime.strptime(data, '%Y-%m-%dT%H:%M')

        disponibilidades = DisponibilidadeHorarios.objects.filter(mentor=request.user).filter(
            data_inicial__gte=(data - timedelta(minutes=50)),
            data_inicial__lte=(data + timedelta(minutes=50))
        )

        if disponibilidades.exists():
            messages.add_message(request, constants.ERROR, 'Você já possui uma reunião em aberto')
            return redirect('reunioes')

        disponibilidades = DisponibilidadeHorarios(
            data_inicial=data,
            mentor=request.user,   
        )
        disponibilidades.save()

        messages.add_message(request, constants.SUCCESS, 'Horário disponibilizado com sucesso.')
        return redirect('reunioes')
    
def auth(request):
 if request.method == 'GET':
  return render(request, 'auth_mentorado.html')
 elif request.method == 'POST':
     token= request.POST.get('token')

     if not Mentorados.objects.filter(token=token).exists():
      messages.add_message(request, constants.ERROR, 'Token inválido')
      return redirect('auth_mentorado')
     
     response = redirect('escolher_dia')
     response.set_cookie('auth_token', token, max_age=3600)

     return response


def escolher_dia(request):
    mentorado = valida_token(request.COOKIES.get('auth_token'))
    if not mentorado:
        return redirect('auth_mentorado')

    if request.method == 'GET':
        hoje = datetime.now().date()  
        disponibilidades = DisponibilidadeHorarios.objects.filter(
            data_inicial__date__gte=hoje,
            agendado=False,
            mentor=mentorado.user
        )
        datas = [
            {
                'dia': data.data_inicial.strftime('%d'),
                'mes': data.data_inicial.strftime('%B'),
                'dia_semana': data.data_inicial.strftime('%A'),
                'data_completa': data.data_inicial.strftime('%d-%m-%Y')
            }
            for data in disponibilidades
        ]
        return render(request, 'escolher_dia.html', {'horarios': datas})

def agendar_reuniao(request):
    if not valida_token(request.COOKIES.get('auth_token')):
        return redirect('auth_mentorado')
    
    mentorado = valida_token(request.COOKIES.get('auth_token'))
    
    if request.method == 'GET':
        data = request.GET.get('data')
        if data:
            data = datetime.strptime(data, '%d-%m-%Y')
            if mentorado:
                horarios = DisponibilidadeHorarios.objects.filter(
                    data_inicial__date=data.date(),
                    agendado=False,
                    mentor=mentorado.user
                )
                return render(request, 'agendar_reuniao.html', {'horarios': horarios, 'tags': Reuniao.tag_choices})
        
     
        return render(request, 'agendar_reuniao.html', {'horarios': [], 'tags': Reuniao.tag_choices})
    
    elif request.method == 'POST':
        horario_id = request.POST.get('horario')
        tag = request.POST.get('tag')
        descricao = request.POST.get('descricao')

        if horario_id and tag and descricao:
            try:
                disponibilidade = DisponibilidadeHorarios.objects.get(id=horario_id, agendado=False)
                disponibilidade.agendado = True
                disponibilidade.save()

                Reuniao.objects.create(
                    data=disponibilidade,
                    mentorado=valida_token(request.COOKIES.get('auth_token')),
                    tag=tag,
                    descricao=descricao
                )

                messages.add_message(request, constants.SUCCESS, 'Reunião agendada com sucesso!')
                return redirect('escolher_dia')
            except DisponibilidadeHorarios.DoesNotExist:
                messages.add_message(request, constants.ERROR, 'Horário não disponível.')
                return redirect('agendar_reuniao')
        
      
        messages.add_message(request, constants.ERROR, 'Todos os campos são obrigatórios.')
        return redirect('agendar_reuniao')
    
 
    return redirect('escolher_dia')