from django.test import TestCase

# testando rota /pacientes
from rest_framework.test import APITestCase
from .models import Paciente

class PacienteViewTest(APITestCase):

    def test_retorna_dados_mascarados(self):

        Paciente.objects.create(
            cns="123456789012345",
            nome="Testando Marques Melo",
            ano_nascimento=2000,
            sexo="M"
        )

        response = self.client.get("/pacientes/")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data[0]["cns"],
            "***********2345"
        )

        self.assertEqual(
            response.data[0]["nome"],
            "T******* M****** M***"
        )