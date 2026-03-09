import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PortasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portas"

    def ready(self):
        # Em desenvolvimento com runserver, o Django cria 2 processos (reloader + servidor).
        # Só iniciamos o scheduler no processo filho (RUN_MAIN=true).
        # Em produção (gunicorn, etc.) RUN_MAIN não é definido — sempre iniciamos.
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
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
            logger.info("APScheduler iniciado — sync Bimer às %s (dias: %s)", horarios, dias)
        except Exception:
            logger.exception("Falha ao iniciar APScheduler")
