import re

from core.brain import Brain
from memory.memory_manager import MemoryManager
from tools.file_intelligence_tools import FileIntelligenceTools
from tools.file_tools import FileTools
from tools.system_tools import SystemTools
from workspace.session_manager import SessionManager


class CommandRouter:
    def __init__(self):
        self.memory = MemoryManager()
        self.brain = Brain(memory_manager=self.memory)
        self.file_intelligence = FileIntelligenceTools()
        self.sessions = SessionManager()

    @staticmethod
    def _normalize_direct_command(user_input):
        """Normalize natural direct commands without invoking an AI model.

        Voice users naturally say things like "hey Jarvis", "Jarvis, time", or
        "hello Jarvis". Treating those as model prompts makes basic desktop
        control slower and unnecessarily dependent on an external provider.
        """
        command = str(user_input or "").lower().strip()
        command = re.sub(r"[^a-z0-9'\s]", " ", command)
        command = re.sub(r"\s+", " ", command).strip()

        if command.startswith("jarvis "):
            command = command[7:].strip()
        if command.endswith(" jarvis"):
            command = command[:-7].strip()
        return command

    def route(self, user_input):
        command = self._normalize_direct_command(user_input)

        if command in ["jarvis", "hey jarvis", "sun jarvis", "jarvis sun", "jarvis sun na"]:
            return "Haan bhai, bol."

        if command in [
            "jarvis tujhe kisne banaya", "tujhe kisne banaya",
            "jarvis kisne banaya", "who made you", "who created you",
            "who developed you", "who built you",
        ]:
            return (
                "Main JARVIS-OS project ka AI assistant hoon, "
                "jise Tarun apne computer ke liye build kar raha hai. "
                "Main Apple ka assistant nahi hoon."
            )

        if command in ["hello", "hi", "hey", "good morning", "good evening"]:
            return self.greeting()

        if command in ["clear conversation", "clear chat history", "forget this conversation"]:
            builder = self.brain.orchestrator.context_builder
            count = builder.clear_conversation() if hasattr(builder, "clear_conversation") else 0
            return f"Cleared {count} saved conversation turn(s). Other project memory and task history were not changed."

        if command in (
            "speak casually", "talk casually", "casual mode",
            "baat kar bhai", "hinglish mode", "speak in hinglish",
            "jarvis speak in hinglish",
        ):
            self.memory.remember(
                "conversation_style",
                "Natural conversational Hinglish, short replies unless detail is requested; "
                "no scripted greetings, feature menus, or unnecessary emoji.",
            )
            return "Theek hai bhai, ab naturally Hinglish mein baat karunga."

        if command in ("english mode", "speak in english"):
            self.memory.remember(
                "conversation_style",
                "Natural English, concise unless detail is requested; "
                "no scripted greetings, feature menus, or unnecessary emoji.",
            )
            return "Got it. I'll use natural English."

        if command in ("ai models", "list ai models", "available models"):
            return self.list_ai_models()
        if command in ("ai model", "active ai model"):
            return self.active_ai_model()
        if command in ("ai model auto", "reset ai model"):
            return self.reset_ai_model()
        if command.startswith("ai model "):
            # The normalized command drops ':' from tags like gemma3:4b.
            # Extract the actual tag from original input, not normalized text.
            original = str(user_input or "").strip()
            match = re.fullmatch(
                r"(?:jarvis[\s,]+)?ai model\s+(.+?)\s*",
                original,
                flags=re.IGNORECASE,
            )
            return self.select_ai_model(match.group(1) if match else "")

        if command in ["chat diagnostics", "conversation diagnostics"]:
            return self.chat_diagnostics()

        if command in ["chat probe", "conversation probe"]:
            return self.chat_probe()

        if command in ["help", "commands"]:
            return self.help()

        if command in [
            "time",
            "what time is it",
            "what is time",
            "what is the time",
            "what's the time",
            "whats the time",
            "tell me the time",
            "current time",
            "time now",
        ]:
            return self.current_time()

        if command in ["who are you", "what are you", "your name"]:
            return self.identity()

        if command in ["system", "system info", "system information"]:
            return self.system_info()

        if command in ["daily brief", "accountability brief", "today brief"]:
            return self.brain.daily_brief()

        if command in [
            "continue my project",
            "continue project",
            "resume project",
            "resume workspace",
            "continue my work",
            "let's continue",
            "lets continue",
        ]:
            return self.resume_workspace()

        if command in ["workspace", "current workspace", "workspace status"]:
            return self.workspace_status()

        if command in ["workspaces", "projects", "recent projects", "recent work"]:
            return self.list_workspaces()

        if command.startswith("resume workspace "):
            return self.resume_workspace(command[17:].strip())

        if command.startswith("resume project "):
            return self.resume_workspace(command[15:].strip())

        if command.startswith("continue project "):
            return self.resume_workspace(command[17:].strip())

        if command in ["list files", "files", "show files"]:
            return self.list_files()

        if command in ["index files", "refresh file index", "reindex files"]:
            return self.index_files()

        if command in ["file index", "file index status"]:
            return self.file_index_status()

        if command.startswith("find file "):
            return self.search_files(command[10:].strip())

        if command.startswith("search files "):
            return self.search_files(command[13:].strip())

        if command in ["tasks", "show tasks", "list tasks"]:
            return self.list_tasks()

        if command.startswith("task "):
            return self.task_status(command[5:].strip())

        if command in ["approvals", "pending approvals"]:
            return self.list_approvals()

        if command.startswith("approve "):
            return self.brain.resolve_approval(command[8:].strip(), approved=True)

        if command.startswith("deny "):
            return self.brain.resolve_approval(command[5:].strip(), approved=False)

        if command == "memories":
            return self.memory.get_all()

        if command.startswith("remember "):
            content = str(user_input or "")[9:].strip()

            if "=" in content:
                key, value = content.split("=", 1)
                return self.memory.remember(key.strip(), value.strip())

            return "Use: remember key = value"

        if command.startswith("recall "):
            key = command[7:].strip()
            return self.memory.recall(key)

        if command.startswith("forget "):
            key = command[7:].strip()
            return self.memory.forget(key)

        return self.brain.respond(user_input)

    def greeting(self):
        return "Haan bhai, bol."

    def help(self):
        return (
            "Currently available commands:\n"
            "  • hello\n"
            "  • time\n"
            "  • system info\n"
            "  • daily brief\n"
            "  • workspace\n"
            "  • workspaces\n"
            "  • continue my project\n"
            "  • resume project <name>\n"
            "  • list files\n"
            "  • index files\n"
            "  • file index status\n"
            "  • find file <description>\n"
            "  • search files <query>\n"
            "  • tasks\n"
            "  • task <id>\n"
            "  • approvals\n"
            "  • approve <id>\n"
            "  • deny <id>\n"
            "  • remember key = value\n"
            "  • recall <key>\n"
            "  • forget <key>\n"
            "  • who are you\n"
            "  • exit"
        )

    def _ollama_provider(self):
        return self.brain.orchestrator.model_router.registry.get("ollama")

    def list_ai_models(self):
        try:
            provider = self._ollama_provider()
            models = provider.installed_models()
        except Exception:
            return "Cannot list local models. Check that Ollama is running."
        if not models:
            return (
                "No Ollama models installed. In PowerShell use "
                "'ollama pull gemma3:4b' or 'ollama pull nemotron-3-nano:4b'."
            )
        lines = [
            "Installed Ollama models (no download or model call performed):",
        ]
        for model in models:
            label = " [selected]" if model == provider.selected_model else (
                " [active/default]" if model == provider.model else ""
            )
            lines.append(f"  {model}{label}")
        lines.append("To switch: ai model <exact model name from this list>")
        lines.append("To reset: ai model auto")
        return "\n".join(lines)

    def active_ai_model(self):
        provider = self._ollama_provider()
        mode = "pinned" if provider.selected_model else "configured default/fallback"
        return f"JARVIS Ollama model: {provider.model} ({mode})."

    def select_ai_model(self, model):
        try:
            provider = self._ollama_provider()
            chosen = provider.choose_model(model)
        except ValueError as error:
            return str(error)
        except Exception:
            return "Could not switch models. Check Ollama connection and local settings path."
        self.brain.orchestrator.model_router.default_provider = "ollama"
        return (
            f"Selected local Ollama model: {chosen}. "
            "This choice persists after restart. Model loading occurs on the next "
            "AI request; no download or background execution was started."
        )

    def reset_ai_model(self):
        try:
            provider = self._ollama_provider()
            configured = provider.reset_model()
        except OSError:
            return "Could not reset the saved AI model selection."
        return f"Model selection reset. Configured Ollama default: {configured}."

    def chat_probe(self):
        """Two controlled local model calls with no memory or desktop tools.

        Explicitly invoked by the user. Does not store the synthetic probes as
        conversation turns and never calls cloud providers or takes actions.
        """
        from time import perf_counter

        registry = self.brain.orchestrator.model_router.registry
        try:
            provider = registry.get("ollama")
        except Exception:
            return "Ollama is not configured for this installation."
        if not provider.is_available:
            return "Local Ollama provider is unavailable."
        prompts = (
            "Give one specific fact about black holes in one sentence. Do not introduce yourself.",
            "Define a Python function in one sentence. Do not introduce yourself.",
        )
        lines = ["JARVIS local chat probe: two independent, history-free model requests."]
        responses = []
        for index, prompt in enumerate(prompts, start=1):
            started = perf_counter()
            try:
                answer = str(provider.generate(user_input=prompt, context=None, tools=None)).strip()
            except Exception as error:
                # Avoid embedding provider errors that may contain sensitive data.
                return (
                    "Local chat probe failed on request "
                    f"{index}: {type(error).__name__}. "
                    "Verify Ollama is running and has the configured model installed."
                )
            responses.append(answer)
            lines.append(
                f"Probe {index} | model={provider.model} | "
                f"elapsed_ms={round((perf_counter()-started)*1000)} | "
                f"answer: {answer[:500] if answer else '[empty response]'}"
            )
        from core.conversation_quality import is_stale_reply
        repeated = is_stale_reply(
            prompts[1],
            responses[1],
            [{"user_text": prompts[0], "assistant_text": responses[0]}],
        )
        lines.append(
            "Probe result: unrelated repeated answers detected."
            if repeated else
            "Probe result: no long near-duplicate detected; check answer relevance manually."
        )
        lines.append(
            "The probe bypasses JARVIS conversation memory, UI and agent routing; "
            "it does not prove normal chat is working."
        )
        return "\n".join(lines)

    def chat_diagnostics(self):
        """Show selected model and response repetition without exposing chat text.

        This command is deliberately local: no new model calls, no API keys,
        raw prompts, saved assistant responses, or provider error strings.
        """
        orchestrator = self.brain.orchestrator
        router = orchestrator.model_router
        tasks = [
            item for item in orchestrator.task_store.list(limit=30)
            if item.intent == "conversation"
        ][:5]
        disabled = ", ".join(sorted(getattr(router, "disabled_providers", set()))) or "none"
        lines = [
            "JARVIS chat diagnostics (local, no AI call)",
            f"Routing preference: {getattr(router, 'default_provider', 'unknown')}",
            f"Routing mode: {getattr(router, 'routing_mode', 'unknown')}",
            f"Disabled providers: {disabled}",
            "Recent model-backed conversation tasks (newest first):",
        ]
        if not tasks:
            lines.append("  No conversation tasks yet. Direct local commands do not create AI tasks.")
            return "\n".join(lines)

        seen_responses = {}
        for task in tasks:
            meta = task.metadata or {}
            attempts = meta.get("routing_attempts") or []
            route = ", ".join(
                f"{item.get('provider', '?')}:{item.get('status', '?')}"
                for item in attempts if isinstance(item, dict)
            ) or "none recorded"
            output = str(task.result or "").strip()
            duplicate = False
            if len(output) >= 70 and task.status.value == "completed":
                from hashlib import sha256
                fingerprint = sha256(output.casefold().encode("utf-8")).hexdigest()
                duplicate = fingerprint in seen_responses
                seen_responses[fingerprint] = True
            trace = meta.get("model_trace") or {}
            lines.append(
                f"  {task.task_id[:8]} | status={task.status.value} | "
                f"provider={meta.get('provider') or 'none'} | "
                f"model={meta.get('model') or 'unknown'} | "
                f"retry={meta.get('conversation_retry') or 'none'} | "
                f"duplicate_reply={'yes' if duplicate else 'no'} | "
                f"input_chars={trace.get('input_chars', 'n/a')} | "
                f"context_chars={trace.get('context_chars', 'n/a')} | "
                f"output_chars={trace.get('response_chars', 'n/a')} | "
                f"model_ms={trace.get('elapsed_ms', 'n/a')} | routes={route}"
            )
        lines.append(
            "If direct Ollama answers differ but these tasks use a different "
            "model/provider, align JARVIS_PROVIDER and OLLAMA_MODEL in .env. "
            "Do not share API keys or the entire .env file."
        )
        return "\n".join(lines)

    def system_info(self):
        info = SystemTools.get_system_info()
        return (
            f"System: {info['system']}\n"
            f"Release: {info['release']}\n"
            f"Machine: {info['machine']}\n"
            f"Processor: {info['processor']}"
        )

    def current_time(self):
        return f"The current time is {SystemTools.get_time()}."

    def identity(self):
        return "I am JARVIS, your personal AI operating environment."

    def workspace_status(self):
        return self.sessions.describe_resume()

    def list_workspaces(self):
        workspaces = self.sessions.store.list_workspaces(limit=10)
        if not workspaces:
            return "No JARVIS workspaces are registered yet."

        lines = []
        for workspace in workspaces:
            lines.append(
                f"- {workspace['name']}\n"
                f"  {workspace['root_path']}\n"
                f"  preferred app: {workspace.get('preferred_app') or 'not set'}"
            )
        return "Recent workspaces:\n" + "\n".join(lines)

    def resume_workspace(self, reference=None):
        result = self.sessions.resume_workspace(reference=reference, launch=True)
        return result["message"]

    def list_files(self):
        return FileTools.list_files()

    def index_files(self):
        result = self.file_intelligence.index_files()
        roots = "\n".join(f"  - {root}" for root in result["roots"])
        return (
            f"File index refreshed. Indexed {result['indexed']} files "
            f"({result['skipped']} skipped).\n"
            f"FTS5: {'enabled' if result['fts'] else 'fallback search'}\n"
            f"Roots:\n{roots}"
        )

    def file_index_status(self):
        status = self.file_intelligence.file_index_status()
        roots = "\n".join(f"  - {root}" for root in status["roots"])
        return (
            f"Indexed files: {status['files']}\n"
            f"Indexed bytes: {status['bytes']}\n"
            f"FTS5: {'enabled' if status['fts'] else 'fallback search'}\n"
            f"Roots:\n{roots}"
        )

    def search_files(self, query):
        if not query:
            return "Use: find file <description>"

        result = self.file_intelligence.search_files(query=query, limit=10)
        matches = result["matches"]
        if not matches:
            return (
                f"No indexed files matched '{query}'. "
                "Run 'index files' if the index may be stale."
            )

        lines = []
        for match in matches:
            lines.append(f"- {match['name']}\n  {match['path']}")
        return f"File matches for '{query}':\n" + "\n".join(lines)

    def list_tasks(self):
        tasks = self.brain.list_tasks(limit=10)
        if not tasks:
            return "No JARVIS tasks have been recorded yet."

        lines = []
        for task in tasks:
            lines.append(
                f"{task.task_id[:8]}  {task.status.value:<16} "
                f"{task.intent:<12}  {task.raw_input[:60]}"
            )
        return "Recent tasks:\n" + "\n".join(lines)

    def task_status(self, task_reference):
        task = self.brain.get_task(task_reference)
        if task is None:
            return f"I could not find a unique task matching '{task_reference}'."

        details = [
            f"Task: {task.task_id}",
            f"Intent: {task.intent}",
            f"Status: {task.status.value}",
            f"Background: {task.background}",
        ]
        if task.metadata.get("agent"):
            details.append(f"Agent: {task.metadata['agent']}")
        if task.result:
            details.append(f"Result: {task.result}")
        if task.error:
            details.append(f"Error: {task.error}")
        return "\n".join(details)

    def list_approvals(self):
        approvals = self.brain.list_approvals(limit=20)
        if not approvals:
            return "No pending approvals."

        lines = []
        for request in approvals:
            lines.append(
                f"{request['approval_id'][:8]}  {request['action']}  "
                f"level={request['permission_level']}"
            )
        return "Pending approvals:\n" + "\n".join(lines)
