from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Paciente
from .serializers import PacienteSerializer


class PacienteListView(APIView):
    def get(self, request):
        pacientes = Paciente.objects.all()

        serializer = PacienteSerializer(
            pacientes,
            many=True
        )

        return Response(serializer.data)
