"""
Notificações — Teams (Incoming Webhook) e e-mail (SMTP).
Nenhum dado sensível é logado ou persistido aqui.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests


# ──────────────────────────────────────────────────
# Teams
# ──────────────────────────────────────────────────

def enviar_teams(webhook_url: str, obra_nome: str, notas_novas: list[dict]) -> None:
    if not webhook_url or not notas_novas:
        return

    linhas = []
    for n in notas_novas[:15]:   # máx 15 linhas para não truncar a mensagem
        try:
            valor_fmt = f"R$ {float(str(n.get('valor','0')).replace(',','.')):,.2f}"
        except (ValueError, TypeError):
            valor_fmt = n.get("valor") or "—"

        data  = n.get("data_emissao", "")[:10] or "—"
        num   = n.get("numero", "—")
        nome  = (n.get("nome_prest") or "—")[:35]
        linhas.append(f"| {data} | {num} | {nome} | {valor_fmt} |")

    tabela = "\n".join(linhas)
    rodape = f"\n\n*... e mais {len(notas_novas)-15} nota(s).*" if len(notas_novas) > 15 else ""

    payload = {
        "@type":    "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "C0392B",
        "summary": f"{len(notas_novas)} NFS-e pendente(s) — {obra_nome}",
        "sections": [{
            "activityTitle":    f"⚠️ {len(notas_novas)} NFS-e não lançada(s) no Sienge",
            "activitySubtitle": f"Obra: **{obra_nome}**",
            "text": (
                "Notas emitidas no SEFAZ que ainda não foram lançadas como título.\n\n"
                "| Data | Nº NFS-e | Prestador | Valor |\n"
                "|------|----------|-----------|-------|\n"
                f"{tabela}{rodape}"
            ),
        }],
    }

    try:
        r = requests.post(webhook_url, json=payload, timeout=15)
        if r.status_code not in (200, 202):
            print(f"  [Teams] Erro: {r.status_code} — {r.text[:100]}")
        else:
            print(f"  [Teams] Mensagem enviada ({len(notas_novas)} nota(s)).")
    except Exception as e:
        print(f"  [Teams] Falha ao enviar: {e}")


# ──────────────────────────────────────────────────
# E-mail via SMTP
# ──────────────────────────────────────────────────

def enviar_email(
    destinatarios: list[str],
    obra_nome: str,
    notas_novas: list[dict],
) -> None:
    smtp_host   = os.environ.get("SMTP_HOST", "")
    smtp_port   = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user   = os.environ.get("SMTP_USER", "")
    smtp_senha  = os.environ.get("SMTP_SENHA", "")

    if not smtp_host or not smtp_user or not destinatarios:
        print("  [E-mail] Configuração SMTP ausente — pulando.")
        return

    linhas_html = ""
    for n in notas_novas:
        try:
            valor_fmt = f"R$ {float(str(n.get('valor','0')).replace(',','.')):,.2f}"
        except (ValueError, TypeError):
            valor_fmt = n.get("valor") or "—"
        linhas_html += (
            f"<tr>"
            f"<td>{n.get('data_emissao','')[:10] or '—'}</td>"
            f"<td>{n.get('numero','—')}</td>"
            f"<td>{n.get('nome_prest','—')}</td>"
            f"<td style='text-align:right'>{valor_fmt}</td>"
            f"</tr>\n"
        )

    html = f"""
<html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
<h2 style="color:#7B2C2C">⚠ {len(notas_novas)} NFS-e pendente(s) — {obra_nome}</h2>
<p>As seguintes notas foram encontradas no SEFAZ mas ainda não estão lançadas no Sienge:</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
  <tr style="background:#7B2C2C;color:white">
    <th>Data Emissão</th><th>Nº NFS-e</th><th>Prestador</th><th>Valor</th>
  </tr>
  {linhas_html}
</table>
<p style="color:#666;font-size:0.85em;margin-top:1rem">
  Monitor NFS-e — INVCP &bull; Fonte: SEFAZ ADN Nacional
</p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[NFS-e] {len(notas_novas)} pendente(s) — {obra_nome}"
    msg["From"]    = smtp_user
    msg["To"]      = ", ".join(destinatarios)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as srv:
            srv.starttls()
            srv.login(smtp_user, smtp_senha)
            srv.sendmail(smtp_user, destinatarios, msg.as_string())
        print(f"  [E-mail] Enviado para {destinatarios}.")
    except Exception as e:
        print(f"  [E-mail] Falha: {e}")
