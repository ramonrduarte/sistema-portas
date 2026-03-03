from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sincroniza preços dos produtos com a API do Bimer"

    def handle(self, *args, **options):
        from portas.services.bimer import sincronizar_precos

        self.stdout.write("Iniciando sincronização com o Bimer...")
        resultado = sincronizar_precos()

        if resultado.get("status") == "inativo":
            self.stdout.write(self.style.WARNING("Integração desativada. Nada feito."))
            return

        if resultado.get("status") == "erro_auth":
            self.stdout.write(self.style.ERROR(f"Erro de autenticação: {resultado.get('msg')}"))
            return

        atualizados = resultado.get("atualizados", 0)
        erros = resultado.get("erros", [])

        self.stdout.write(self.style.SUCCESS(f"{atualizados} produto(s) atualizado(s)."))
        if erros:
            self.stdout.write(self.style.WARNING(f"{len(erros)} erro(s):"))
            for e in erros:
                self.stdout.write(f"  - {e}")
