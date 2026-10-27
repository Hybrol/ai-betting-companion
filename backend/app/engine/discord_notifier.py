import logging
from datetime import datetime
import httpx
from ..core.config import settings

logger = logging.getLogger(__name__)

MARKET_LABELS_PT = {
    "1X2": "1X2 (Resultado Final)",
    "DOUBLE_CHANCE": "Dupla Chance / Hipótese Dupla",
    "OVER_UNDER_1_5": "Total de Golos (Mais/Menos 1.5)",
    "OVER_UNDER_2_5": "Total de Golos (Mais/Menos 2.5)",
    "OVER_UNDER_3_5": "Total de Golos (Mais/Menos 3.5)",
    "BTTS": "Ambas as Equipas Marcam",
}

SELECTION_LABELS_PT = {
    "1": "Vitória Casa (1)",
    "X": "Empate (X)",
    "2": "Vitória Fora (2)",
    "1X": "1X (Casa ou Empate)",
    "X2": "X2 (Empate ou Fora)",
    "12": "12 (Casa ou Fora)",
    "OVER": "Mais de (Over)",
    "UNDER": "Menos de (Under)",
    "YES": "Sim (Ambas Marcam)",
    "NO": "Não (Pelo menos uma não marca)",
}

class DiscordNotifier:
    @staticmethod
    async def send_webhook_message(embeds: list[dict], content: str = "") -> bool:
        webhook_url = settings.DISCORD_WEBHOOK_URL
        if not webhook_url:
            logger.debug("Discord Webhook URL not configured. Skipping webhook.")
            return False

        payload = {
            "username": "AI Tipster de Elite (SRIJ)",
            "avatar_url": "https://img.icons8.com/color/96/football2--v1.png",
            "content": content,
            "embeds": embeds
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url, json=payload)
                if res.status_code in (200, 204):
                    logger.info("Successfully sent Discord webhook notification.")
                    return True
                else:
                    logger.error(f"Failed to send Discord webhook: HTTP {res.status_code} - {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error dispatching Discord webhook: {e}")
            return False

    @classmethod
    async def notify_value_bet(
        cls,
        home_team: str,
        away_team: str,
        league: str,
        kickoff: datetime,
        market_type: str,
        selection: str,
        best_bookmaker: str,
        best_odds: float,
        model_prob: float,
        fair_odds: float,
        ev_percent: float,
        recommended_stake: float,
        confidence: str = "MÉDIA",
        reasoning: str = "",
        auto_bet_placed: bool = False
    ) -> bool:
        kickoff_str = kickoff.strftime("%d/%m/%Y às %H:%M")
        market_name = MARKET_LABELS_PT.get(market_type, market_type)
        sel_name = SELECTION_LABELS_PT.get(selection, selection)

        color = 0x10b981 if confidence == "ALTA" else 0x3b82f6 # Emerald or Blue

        embed = {
            "title": f"🎯 Aposta de Valor: {home_team} vs {away_team}",
            "description": (
                f"⚽ **Jogo + Hora:** `{home_team} vs {away_team}` • **{kickoff_str}**\n"
                f"🏆 **Competição:** `{league}`\n"
                f"📋 **Mercado Exato:** `{market_name}` — **{sel_name}**\n"
                f"💰 **Odd + Casa:** **`{best_odds:.2f}`** na **{best_bookmaker}** (SRIJ)\n\n"
                f"📊 **Análise Quantitativa:**\n"
                f"• Odd Justa Calculada: `{fair_odds:.2f}` (Prob: `{model_prob * 100:.1f}%`)\n"
                f"• Margem (+EV): **`+{ev_percent:.1f}%`** | Stake Sugerida: **`{recommended_stake:.2f} €`**\n\n"
                f"💡 **Nível de Confiança & Razão do Valor:**\n"
                f"> **Confiança {confidence}:** {reasoning if reasoning else 'Edge estatístico verificado face ao modelo de mercado.'}\n"
            ),
            "color": color,
            "fields": [
                {
                    "name": "⚡ Estado da Paper Bet",
                    "value": "✅ **Aposta simulada registada na banca virtual!**" if auto_bet_placed else "ℹ️ Análise disponível no dashboard.",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"{settings.RESPONSIBLE_GAMBLING_MSG} • AI Betting Companion"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        return await cls.send_webhook_message(embeds=[embed])

    @classmethod
    async def notify_curated_multiple(cls, multiple_data: dict) -> bool:
        if not multiple_data or multiple_data.get("legs_count", 0) < 2:
            return False

        legs = multiple_data.get("legs", [])
        legs_text = []
        for i, leg in enumerate(legs, 1):
            mkt = MARKET_LABELS_PT.get(leg["market"], leg["market"])
            sel = SELECTION_LABELS_PT.get(leg["selection"], leg["selection"])
            conf_icon = "🟢" if leg.get("confidence") == "ALTA" else "🔵"
            
            dossier = leg.get("dossier_text", "")
            if dossier:
                analysis_part = f"\n   {dossier}"
            else:
                analysis_part = f"\n   • *{leg.get('reasoning', '')}*"

            legs_text.append(
                f"**{i}. {leg['match']}** ({leg.get('league', '')})\n"
                f"   • Mercado: `{mkt}` — `{sel}`\n"
                f"   • Odd: **`{leg['odds']:.2f}`** na **{leg['bookmaker']}** {conf_icon} *Confiança {leg.get('confidence', 'ALTA')}*"
                f"{analysis_part}"
            )

        description = (
            f"Combinação de valor selecionada com base em análise estatística aprofundada, Dixon-Coles e consenso SRIJ:\n\n"
            + "\n\n".join(legs_text) + "\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 **Odd Total Combinada:** **`{multiple_data['total_odds']:.2f}`** (Odd Justa: `{multiple_data['fair_odds']:.2f}`)\n"
            f"🎯 **Probabilidade Estimada:** `{multiple_data['combined_prob_percent']}%` | Edge: **`+{multiple_data['combined_ev_percent']}%`**\n"
            f"💵 **Stake Controlada:** **`{multiple_data['recommended_stake']:.2f} €`** ➜ Potencial Retorno: **`{multiple_data['potential_payout']:.2f} €`**\n"
            f"📝 **Paper Wager:** Aposta combinada registada automaticamente no sistema.\n"
        )

        embed = {
            "title": f"💎 Múltipla de Valor do Dia ({multiple_data['legs_count']} Seleções)",
            "description": description,
            "color": 0x8b5cf6, # Purple / Diamond
            "footer": {
                "text": f"{settings.RESPONSIBLE_GAMBLING_MSG} • AI Betting Companion"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        return await cls.send_webhook_message(embeds=[embed])

    @classmethod
    async def notify_multiple_result(
        cls,
        bet_id: int,
        legs: list[dict],
        odds: float,
        stake: float,
        profit_loss: float,
        is_green: bool,
        current_balance: float
    ) -> bool:
        if not settings.DISCORD_WEBHOOK_URL:
            return False

        title = f"{'🎉 MÚLTIPLA DE VALOR GREEN!' if is_green else '❌ Múltipla de Valor Resolvida (RED)'}"
        color = 0x22c55e if is_green else 0xef4444

        legs_summary = []
        for idx, l in enumerate(legs, 1):
            leg_icon = "✅" if l.get("status") == "GREEN" else ("❌" if l.get("status") == "RED" else "⏳")
            legs_summary.append(f"{leg_icon} **{l.get('match')}**: `{l.get('market')}` - `{l.get('selection')}` @ {l.get('odds')}")

        pnl_text = f"+{profit_loss:.2f} €" if is_green else f"{profit_loss:.2f} €"

        desc = (
            f"**Resultado Final da Múltipla #{bet_id} ({len(legs)} Seleções):**\n\n"
            + "\n".join(legs_summary) + "\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 **Odd Total:** `{odds:.2f}` | Stake: `{stake:.2f} €`\n"
            f"💰 **Retorno:** **`{pnl_text}`**\n"
            f"🏦 **Banca Atualizada:** `{current_balance:.2f} €`"
        )

        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "footer": {
                "text": f"{settings.RESPONSIBLE_GAMBLING_MSG} • AI Betting Companion"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        return await cls.send_webhook_message(embeds=[embed])

    @classmethod
    async def notify_bet_result(
        cls,
        home_team: str,
        away_team: str,
        league: str,
        home_score: int,
        away_score: int,
        market_type: str,
        selection: str,
        bookmaker: str,
        odds: float,
        stake: float,
        profit_loss: float,
        is_green: bool,
        current_balance: float
    ) -> bool:
        market_name = MARKET_LABELS_PT.get(market_type, market_type)
        sel_name = SELECTION_LABELS_PT.get(selection, selection)
        score_str = f"{home_team} {home_score} - {away_score} {away_team}"

        if is_green:
            title = f"🎉 APOSTA GANHA (GREEN)! +{profit_loss:.2f} €"
            color = 0x10b981  # Emerald
            status_text = f"✅ **GREEN!** Retorno líquido: **`+{profit_loss:.2f} €`** (Odd `{odds:.2f}`)"
        else:
            title = f"❌ Aposta Não Correspondida (RED): {profit_loss:.2f} €"
            color = 0xef4444  # Red
            status_text = f"🛑 **RED.** Perda da stake: `-{stake:.2f} €`"

        embed = {
            "title": title,
            "description": (
                f"⚽ **Resultado Final:** `{score_str}`\n"
                f"🏆 **Competição:** `{league}`\n"
                f"📋 **Mercado Resolvido:** `{market_name}` — **{sel_name}**\n"
                f"💰 **Odd & Casa:** **`{odds:.2f}`** na **{bookmaker}** (SRIJ) | Stake: **`{stake:.2f} €`**\n\n"
                f"{status_text}\n"
                f"💵 **Saldo Atualizado da Banca:** **`{current_balance:.2f} €`**\n"
            ),
            "color": color,
            "footer": {
                "text": f"{settings.RESPONSIBLE_GAMBLING_MSG} • AI Betting Companion"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        return await cls.send_webhook_message(embeds=[embed])

    @classmethod
    async def send_test_notification(cls, webhook_url: str | None = None) -> tuple[bool, str]:
        url = webhook_url or settings.DISCORD_WEBHOOK_URL
        if not url:
            return False, "Nenhum URL de webhook configurado"

        embed = {
            "title": "✅ AI Tipster de Elite: Notificações Ativas",
            "description": (
                "O bot de apostas de valor para casas portuguesas (SRIJ) está conectado a este canal.\n\n"
                "**Ligas Prioritárias Ativas:**\n"
                "• Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Liga Portugal\n"
                "• Champions League, Europa League, Conference League\n"
                "• Saudi Pro League, UAE Pro League, Qatar Stars League\n\n"
                "**Mercados Analisados:**\n"
                "• 1X2, Dupla Chance, Over/Under 1.5/2.5/3.5, Ambas Marcam (BTTS)\n\n"
                f"*{settings.RESPONSIBLE_GAMBLING_MSG}*"
            ),
            "color": 0x10b981,
            "footer": {
                "text": "Portuguese AI Betting Companion • Monitorização 24/7"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "username": "AI Tipster de Elite (SRIJ)",
            "embeds": [embed]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code in (200, 204):
                    return True, "Mensagem de teste enviada com sucesso!"
                else:
                    return False, f"Erro HTTP {res.status_code}: {res.text}"
        except Exception as e:
            return False, str(e)
