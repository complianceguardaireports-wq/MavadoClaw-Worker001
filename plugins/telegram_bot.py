import os
import asyncio
import logging
from typing import Optional

import httpx
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "mavadoclaw-changeme")
MAVADOCLAW_API_URL = os.environ.get("MAVADOCLAW_API_URL", "http://127.0.0.1:8000")


class TelegramBot:
    def __init__(self):
        self.app: Optional[Application] = None
        self.http: Optional[httpx.AsyncClient] = None
        self._notify_task: Optional[asyncio.Task] = None

    async def start(self):
        self.app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )
        self.http = httpx.AsyncClient(
            base_url=MAVADOCLAW_API_URL,
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            timeout=30.0,
        )

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("queue", self.cmd_queue))
        self.app.add_handler(CommandHandler("approve", self.cmd_approve))
        self.app.add_handler(CommandHandler("reject", self.cmd_reject))
        self.app.add_handler(CommandHandler("osint", self.cmd_osint))
        self.app.add_handler(CommandHandler("chat", self.cmd_chat))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.cmd_chat_text)
        )

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

        await self.app.bot.set_my_commands([
            BotCommand("start", "Welcome message"),
            BotCommand("status", "System status"),
            BotCommand("queue", "Pending approval tasks"),
            BotCommand("approve", "Approve a task"),
            BotCommand("reject", "Reject a task"),
            BotCommand("osint", "Launch OSINT scan"),
            BotCommand("chat", "Chat with AI company"),
        ])

        self._notify_task = asyncio.create_task(self._approval_watcher())
        logger.info("Telegram bot started")

    async def stop(self):
        if self._notify_task:
            self._notify_task.cancel()
            try:
                await self._notify_task
            except asyncio.CancelledError:
                pass
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        if self.http:
            await self.http.aclose()
        logger.info("Telegram bot stopped")

    async def _api_get(self, path: str) -> dict:
        resp = await self.http.get(path)
        resp.raise_for_status()
        return resp.json()

    async def _api_post(self, path: str, json: dict = None) -> dict:
        resp = await self.http.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def _send(self, text: str):
        await self.app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

    async def _is_authorized(self, update: Update) -> bool:
        return str(update.effective_chat.id) == TELEGRAM_CHAT_ID

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        await update.message.reply_text(
            "MavadoClaw Bot Online\n\n"
            "/status - System status\n"
            "/queue - Pending approvals\n"
            "/approve <id> - Approve task\n"
            "/reject <id> - Reject task\n"
            "/osint <target> - OSINT scan\n"
            "/chat <message> - Chat with AI"
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        try:
            data = await self._api_get("/status")
            agents = data.get("agents", [])
            providers = data.get("llm_providers", [])
            memory = data.get("memory", {})
            agent_lines = "\n".join(
                f"  - {a.get('name', '?')}: {a.get('status', '?')}" for a in agents
            ) or "  None"
            provider_lines = "\n".join(
                f"  - {p.get('name', '?')}: {p.get('status', '?')}" for p in providers
            ) or "  None"
            await update.message.reply_text(
                f"System Status\n\n"
                f"Agents:\n{agent_lines}\n\n"
                f"LLM Providers:\n{provider_lines}\n\n"
                f"Memory: {memory.get('total_entries', 0)} entries"
            )
        except Exception as e:
            await update.message.reply_text(f"Error fetching status: {e}")

    async def cmd_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        try:
            data = await self._api_get("/approvals/queue")
            tasks = data.get("tasks", [])
            if not tasks:
                await update.message.reply_text("No pending tasks")
                return
            lines = []
            for t in tasks:
                lines.append(
                    f"[{t.get('id', '?')}] {t.get('type', '?')}\n"
                    f"  Agent: {t.get('agent', '?')}\n"
                    f"  Summary: {t.get('summary', '?')}\n"
                    f"  Created: {t.get('created_at', '?')}"
                )
            await update.message.reply_text(
                f"Pending Approvals ({len(tasks)}):\n\n" + "\n\n".join(lines)
            )
        except Exception as e:
            await update.message.reply_text(f"Error fetching queue: {e}")

    async def cmd_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        if not context.args:
            await update.message.reply_text("Usage: /approve <task_id>")
            return
        task_id = context.args[0]
        try:
            await self._api_post(f"/approvals/{task_id}/approve")
            await update.message.reply_text(f"Task {task_id} approved")
        except Exception as e:
            await update.message.reply_text(f"Error approving task: {e}")

    async def cmd_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        if not context.args:
            await update.message.reply_text("Usage: /reject <task_id>")
            return
        task_id = context.args[0]
        try:
            await self._api_post(f"/approvals/{task_id}/reject")
            await update.message.reply_text(f"Task {task_id} rejected")
        except Exception as e:
            await update.message.reply_text(f"Error rejecting task: {e}")

    async def cmd_osint(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        if not context.args:
            await update.message.reply_text("Usage: /osint <target>")
            return
        target = " ".join(context.args)
        await update.message.reply_text(f"Launching OSINT scan on: {target}")
        try:
            data = await self._api_post("/osint/scan", json={"target": target})
            job_id = data.get("job_id", "?")
            await update.message.reply_text(f"OSINT scan started. Job ID: {job_id}")
        except Exception as e:
            await update.message.reply_text(f"Error launching OSINT: {e}")

    async def cmd_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            await update.message.reply_text("Unauthorized")
            return
        if not context.args:
            await update.message.reply_text("Usage: /chat <message>")
            return
        message = " ".join(context.args)
        await update.message.reply_text("Processing...")
        try:
            data = await self._api_post("/chat", json={"message": message})
            reply = data.get("response", "No response")
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def cmd_chat_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_authorized(update):
            return
        message = update.message.text
        try:
            data = await self._api_post("/chat", json={"message": message})
            reply = data.get("response", "No response")
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def _approval_watcher(self):
        notified = set()
        while True:
            try:
                data = await self._api_get("/approvals/queue")
                tasks = data.get("tasks", [])
                for t in tasks:
                    tid = t.get("id")
                    if tid and tid not in notified:
                        notified.add(tid)
                        await self._send(
                            f"Approval Required\n\n"
                            f"ID: {tid}\n"
                            f"Type: {t.get('type', '?')}\n"
                            f"Agent: {t.get('agent', '?')}\n"
                            f"Summary: {t.get('summary', '?')}\n\n"
                            f"Use /approve {tid} or /reject {tid}"
                        )
                current_ids = {t.get("id") for t in tasks}
                notified &= current_ids
            except Exception as e:
                logger.error(f"Approval watcher error: {e}")
            await asyncio.sleep(10)


bot = TelegramBot()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await bot.start()
    try:
        await asyncio.Event().wait()
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
