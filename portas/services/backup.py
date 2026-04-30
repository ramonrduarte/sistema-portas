import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _nome_arquivo(padrao: str) -> str:
    agora = timezone.localtime(timezone.now())
    nome = padrao
    nome = nome.replace("{data}", agora.strftime("%Y%m%d"))
    nome = nome.replace("{hora}", agora.strftime("%H%M"))
    return nome


def _backup_sqlite(dest_dir: Path, nome_base: str) -> Path:
    db_path = settings.DATABASES["default"]["NAME"]
    src = Path(db_path)
    dst = dest_dir / f"{nome_base}.sqlite3"
    shutil.copy2(src, dst)
    return dst


def _backup_postgresql(dest_dir: Path, nome_base: str) -> Path:
    db = settings.DATABASES["default"]
    dst = dest_dir / f"{nome_base}.dump"
    env = os.environ.copy()
    if db.get("PASSWORD"):
        env["PGPASSWORD"] = db["PASSWORD"]
    cmd = [
        "pg_dump",
        "-h", db.get("HOST", "localhost"),
        "-p", str(db.get("PORT", "5432")),
        "-U", db.get("USER", "postgres"),
        "-F", "c",
        "-f", str(dst),
        db["NAME"],
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump falhou: {result.stderr}")
    return dst


def realizar_backup() -> dict:
    """
    Executa o backup do banco de dados, comprime em zip e registra no histórico.
    Escreve primeiro em /tmp para evitar problemas de buffer em montagens de rede (CIFS/NFS),
    depois move o zip final para o diretório de destino configurado.
    """
    from portas.models import ConfiguracaoBackup, HistoricoBackup

    config = ConfiguracaoBackup.get()
    resultado = {"sucesso": False, "arquivo": "", "tamanho_bytes": None, "mensagem": ""}
    tmp_dir = None

    try:
        if not config.diretorio:
            raise ValueError("Diretório de destino não configurado.")

        dest_dir = Path(config.diretorio)
        dest_dir.mkdir(parents=True, exist_ok=True)

        nome_base = _nome_arquivo(config.padrao_nome or "portas_{data}_{hora}")
        engine = settings.DATABASES["default"]["ENGINE"]

        # Usa diretório temporário local para evitar problemas de escrita em rede
        tmp_dir = Path(tempfile.mkdtemp(prefix="portas_backup_"))

        if "sqlite3" in engine:
            arquivo_db = _backup_sqlite(tmp_dir, nome_base)
        elif "postgresql" in engine:
            arquivo_db = _backup_postgresql(tmp_dir, nome_base)
        else:
            raise ValueError(f"Engine de banco não suportada para backup: {engine}")

        # Cria o zip localmente em /tmp
        zip_local = tmp_dir / f"{nome_base}.zip"
        with zipfile.ZipFile(zip_local, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(arquivo_db, arquivo_db.name)

        arquivo_db.unlink(missing_ok=True)

        # Verifica que o zip local foi criado corretamente
        tamanho_local = zip_local.stat().st_size
        if tamanho_local == 0:
            raise RuntimeError("Arquivo zip gerado está vazio.")

        # Move para o destino final (rede/CIFS)
        zip_destino = dest_dir / f"{nome_base}.zip"
        shutil.move(str(zip_local), str(zip_destino))

        # Confirma que o arquivo chegou ao destino
        tamanho_final = zip_destino.stat().st_size
        if tamanho_final == 0:
            raise RuntimeError("Arquivo zip no destino está vazio após a transferência.")

        resultado.update(
            sucesso=True,
            arquivo=str(zip_destino),
            tamanho_bytes=tamanho_final,
            mensagem="Backup concluído com sucesso.",
        )
        logger.info("Backup concluído: %s (%d bytes)", zip_destino, tamanho_final)

    except Exception as exc:
        logger.exception("Falha no backup")
        resultado["mensagem"] = str(exc)

    finally:
        # Remove diretório temporário local em qualquer caso
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    HistoricoBackup.objects.create(
        arquivo=resultado["arquivo"],
        tamanho_bytes=resultado["tamanho_bytes"],
        sucesso=resultado["sucesso"],
        mensagem=resultado["mensagem"],
    )
    # Mantém apenas os últimos 50 registros
    ids_excluir = list(
        HistoricoBackup.objects.values_list("id", flat=True).order_by("-data_hora")[50:]
    )
    if ids_excluir:
        HistoricoBackup.objects.filter(id__in=ids_excluir).delete()

    return resultado
