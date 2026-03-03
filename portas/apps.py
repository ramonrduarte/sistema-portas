import os

from django.apps import AppConfig


class PortasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portas"

    def ready(self):
        # Evita dupla execução no runserver (reloader do Django cria 2 processos)
        if os.environ.get("RUN_MAIN") != "true":
            return
        self._iniciar_scheduler()

    def _iniciar_scheduler(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            from portas import scheduler as sched_module
            from portas.models import BimerConfig
            from portas.services.bimer import sincronizar_precos

            # Lê horários e dias configurados no banco
            config   = BimerConfig.get()
            horarios = config.sync_horarios.strip() or "7,14"
            dias     = config.sync_dias_semana.strip() or "mon,tue,wed,thu,fri,sat,sun"

            scheduler = BackgroundScheduler()
            scheduler.add_job(
                sincronizar_precos,
                CronTrigger(hour=horarios, day_of_week=dias, minute="0"),
                id="bimer_sync",
                replace_existing=True,
            )
            scheduler.start()

            # Armazena referência global para reagendamento dinâmico
            sched_module.set(scheduler)
        except Exception:
            # Não impede o servidor de subir se o APScheduler falhar
            pass
