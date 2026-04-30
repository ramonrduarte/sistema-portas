"""
Referência global ao APScheduler.
Permite que outras partes do sistema (models, views) reagendem jobs
sem importar apps.py (o que causaria import circular).
"""
_scheduler = None


def get():
    return _scheduler


def set(s):
    global _scheduler
    _scheduler = s


def reagendar(horarios: str, dias: str):
    """
    Reagenda o job 'bimer_sync' com os novos horários e dias.
    Chamado automaticamente ao salvar BimerConfig.
    Silencia erros (scheduler pode não estar rodando em ambientes de teste/management).
    """
    try:
        from apscheduler.triggers.cron import CronTrigger

        s = get()
        if s and s.running:
            s.reschedule_job(
                "bimer_sync",
                trigger=CronTrigger(
                    hour=horarios.strip(),
                    day_of_week=dias.strip(),
                    minute="0",
                ),
            )
    except Exception:
        pass


def recarregar_backup():
    """
    Remove todos os jobs de backup existentes e recria a partir dos
    AgendamentoBackup ativos no banco.
    Silencia erros (scheduler pode não estar rodando em test/management).
    """
    try:
        from apscheduler.triggers.cron import CronTrigger
        from portas.models import AgendamentoBackup, ConfiguracaoBackup
        from portas.services.backup import realizar_backup

        s = get()
        if not (s and s.running):
            return

        # Remove jobs de backup anteriores
        for job in s.get_jobs():
            if job.id.startswith("backup_"):
                s.remove_job(job.id)

        config = ConfiguracaoBackup.get()
        if not config.ativo:
            return

        for ag in AgendamentoBackup.objects.all():
            job_id = f"backup_{ag.dia_semana}_{ag.horario.strftime('%H%M')}"
            s.add_job(
                realizar_backup,
                CronTrigger(
                    day_of_week=ag.dia_semana,
                    hour=ag.horario.hour,
                    minute=ag.horario.minute,
                ),
                id=job_id,
                replace_existing=True,
            )
    except Exception:
        pass
