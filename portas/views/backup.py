import logging
import os
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from portas.models import AgendamentoBackup, ConfiguracaoBackup, HistoricoBackup
from portas import scheduler as sched_module

logger = logging.getLogger(__name__)

DIAS_LABEL = dict(AgendamentoBackup.DIAS)


@login_required
@require_POST
def backup_testar_diretorio(request):
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "mensagem": "Sem permissão."}, status=403)

    diretorio = request.POST.get("diretorio", "").strip()
    if not diretorio:
        return JsonResponse({"ok": False, "mensagem": "Nenhum diretório informado."})

    try:
        dest = Path(diretorio)
        dest.mkdir(parents=True, exist_ok=True)

        # Tenta criar e remover um arquivo temporário para confirmar escrita
        tmp = tempfile.NamedTemporaryFile(dir=dest, prefix=".teste_backup_", delete=False)
        tmp.close()
        Path(tmp.name).unlink()

        return JsonResponse({"ok": True, "mensagem": f"Diretório acessível e com permissão de escrita."})
    except PermissionError:
        return JsonResponse({"ok": False, "mensagem": "Sem permissão de escrita neste diretório."})
    except FileNotFoundError:
        return JsonResponse({"ok": False, "mensagem": "Caminho inválido ou não encontrado."})
    except Exception as exc:
        return JsonResponse({"ok": False, "mensagem": str(exc)})


@login_required
def backup_config(request):
    if not request.user.is_staff:
        return redirect("pedidos_lista")

    config = ConfiguracaoBackup.get()
    agendamentos = AgendamentoBackup.objects.all()
    historico = HistoricoBackup.objects.all()[:20]

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "salvar_config":
            config.diretorio = request.POST.get("diretorio", "").strip()
            config.padrao_nome = request.POST.get("padrao_nome", "portas_{data}_{hora}").strip()
            config.ativo = request.POST.get("ativo") == "on"
            config.save()

            # Reconstrói agendamentos a partir do POST
            AgendamentoBackup.objects.all().delete()
            dias = request.POST.getlist("dia_semana")
            horarios = request.POST.getlist("horario")
            erros = 0
            for dia, horario in zip(dias, horarios):
                if dia and horario:
                    try:
                        AgendamentoBackup.objects.get_or_create(dia_semana=dia, horario=horario)
                    except Exception:
                        erros += 1
            if erros:
                messages.warning(request, f"{erros} agendamento(s) duplicado(s) foram ignorados.")

            sched_module.recarregar_backup()
            messages.success(request, "Configurações de backup salvas.")
            return redirect("backup_config")

        if action == "backup_agora":
            from portas.services.backup import realizar_backup
            resultado = realizar_backup()
            if resultado["sucesso"]:
                messages.success(request, f"Backup realizado: {resultado['arquivo']}")
            else:
                messages.error(request, f"Falha no backup: {resultado['mensagem']}")
            return redirect("backup_config")

    ctx = {
        "config": config,
        "agendamentos": agendamentos,
        "historico": historico,
        "dias_choices": AgendamentoBackup.DIAS,
    }
    return render(request, "backup/configuracao.html", ctx)
