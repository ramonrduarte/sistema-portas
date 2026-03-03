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
