import re
from pathlib import Path

from translation_core import (
    GlossaryEntry,
    ProviderConfig,
    create_provider,
    find_relevant_entries,
    get_recent,
    load_agent_file,
    load_chapters,
    load_glossary,
    record_chapter,
    save_agent_file,
    save_glossary,
    translate_chunk,
)

from server import agent_templates
from server import workspace
from server.node_registry import NodeBase, register_node


_DEFAULT_PROVIDER_TIMEOUT_SECONDS = 300.0


def _parse_timeout_seconds(value: str) -> float:
    """Parse the Provider node's timeout_seconds field.

    That field is a plain STRING input like every other node input (the
    node system has no numeric widget), typed and editable by hand -- an
    empty or malformed value falls back to the default rather than
    rejecting the whole run over a typo.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return _DEFAULT_PROVIDER_TIMEOUT_SECONDS


@register_node("Provider")
class Provider(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("PROVIDER",)
    RETURN_NAMES = ("provider",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "model": ("STRING", {"default": ""}),
            },
            "optional": {
                "timeout_seconds": (
                    "STRING",
                    {"default": str(int(_DEFAULT_PROVIDER_TIMEOUT_SECONDS))},
                ),
            },
        }

    def execute(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: str = "",
    ) -> tuple:
        config = ProviderConfig(
            type="openai_compatible",
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=_parse_timeout_seconds(timeout_seconds),
        )
        return (create_provider(config),)


@register_node("LoadAgentFile")
class LoadAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {"template": ("STRING", {"default": "workspace", "widget": "agent_template"})},
        }

    def execute(self, workspace_name: str, template: str = "workspace") -> tuple:
        if template == "workspace":
            path = workspace.get_workspace_path(workspace_name, "agent.md")
        else:
            path = agent_templates.resolve_template_path(template)
        return (load_agent_file(path),)


@register_node("SaveAgentFile")
class SaveAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, workspace_name: str, text: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "agent.md")
        save_agent_file(path, text)
        return ()


@register_node("LoadGlossary")
class LoadGlossary(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("GLOSSARY_ENTRIES",)
    RETURN_NAMES = ("glossary_entries",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "glossary.json")
        return (load_glossary(path),)


@register_node("SaveGlossary")
class SaveGlossary(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"glossary_entries": ("GLOSSARY_ENTRIES", {})}}

    def execute(self, workspace_name: str, glossary_entries) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "glossary.json")
        save_glossary(path, glossary_entries)
        return ()


@register_node("LookupGlossary")
class LookupGlossary(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("GLOSSARY_ENTRIES",)
    RETURN_NAMES = ("relevant_entries",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "glossary_entries": ("GLOSSARY_ENTRIES", {}),
                "text": ("STRING", {"default": ""}),
            }
        }

    def execute(self, glossary_entries, text: str) -> tuple:
        return (find_relevant_entries(glossary_entries, text),)


@register_node("RecordChapter")
class RecordChapter(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chapter_id": ("STRING", {"default": ""}),
                "source_path": ("STRING", {"default": "", "widget": "path"}),
                "output_path": ("STRING", {"default": "", "widget": "path"}),
            }
        }

    def execute(self, workspace_name: str, chapter_id: str, source_path: str, output_path: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "chapters.json")
        record_chapter(path, chapter_id, source_path, output_path)
        return ()


@register_node("Translate")
class Translate(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "agent_instructions": ("STRING", {"default": ""}),
                "source_text": ("STRING", {"default": ""}),
            },
            "optional": {"glossary_entries": ("GLOSSARY_ENTRIES", {})},
        }

    def execute(
        self, provider, agent_instructions: str, source_text: str, glossary_entries=None
    ) -> tuple:
        result = translate_chunk(provider, agent_instructions, glossary_entries or [], source_text)
        return (result,)


_CONFLICT_KEEP_OLD = "GIU_CU"
_CONFLICT_USE_NEW = "DUNG_MOI"


@register_node("ExtractGlossary")
class ExtractGlossary(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("GLOSSARY_ENTRIES", "STRING", "STRING")
    RETURN_NAMES = ("updated_glossary_entries", "corrected_translated_text", "revision_note")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "glossary_entries": ("GLOSSARY_ENTRIES", {}),
                "source_text": ("STRING", {"default": ""}),
                "translated_text": ("STRING", {"default": ""}),
                "chapter_id": ("STRING", {"default": ""}),
            }
        }

    def execute(self, provider, glossary_entries, source_text, translated_text, chapter_id) -> tuple:
        candidates = self._extract_candidates(provider, source_text, translated_text)

        working = list(glossary_entries)
        by_term = {e.term: e for e in working}
        replacements = []
        added = []
        notes = []

        for term, translation, note in candidates:
            existing = by_term.get(term)
            if existing is None:
                entry = GlossaryEntry(term=term, translation=translation, note=note, chapter_id=chapter_id)
                working.append(entry)
                by_term[term] = entry
                added.append(term)
                continue
            if existing.translation == translation:
                continue

            verdict = self._resolve_conflict(provider, existing, term, translation, note)
            if verdict == _CONFLICT_USE_NEW:
                working = [e for e in working if e.term != term]
                new_entry = GlossaryEntry(term=term, translation=translation, note=note, chapter_id=chapter_id)
                working.append(new_entry)
                by_term[term] = new_entry
                notes.append(
                    f"'{term}': đổi từ '{existing.translation}' sang '{translation}' — "
                    "các chương khác dùng bản dịch cũ nên được rà soát lại bằng EvaluateAndFixChapters."
                )
            else:
                replacements.append((term, translation, existing.translation))

        corrected_translated_text = translated_text
        unresolved_notes = []
        safe_pairs = {}
        for term, wrong, correct in replacements:
            if wrong in correct or correct in wrong:
                unresolved_notes.append(
                    f"'{term}': không tự sửa được (chuỗi chồng chéo) — cần sửa tay '{wrong}' → '{correct}'."
                )
                continue
            if translated_text.count(wrong) != source_text.count(term):
                unresolved_notes.append(
                    f"'{term}': không tự sửa được (số lần xuất hiện không khớp) — cần sửa tay '{wrong}' → '{correct}'."
                )
                continue
            safe_pairs[wrong] = correct

        if safe_pairs:
            pattern = re.compile(
                "|".join(re.escape(w) for w in sorted(safe_pairs, key=len, reverse=True))
            )
            corrected_translated_text = pattern.sub(lambda m: safe_pairs[m.group(0)], translated_text)

        summary_lines = []
        if added:
            summary_lines.append("Thuật ngữ mới: " + ", ".join(added))
        summary_lines.extend(notes)
        summary_lines.extend(unresolved_notes)
        if not summary_lines:
            summary_lines.append("Không có thuật ngữ mới hoặc xung đột nào.")

        return (working, corrected_translated_text, "\n".join(summary_lines))

    def _extract_candidates(self, provider, source_text, translated_text):
        messages = [
            {
                "role": "system",
                "content": (
                    "Đọc đoạn văn gốc và bản dịch dưới đây. Liệt kê các thuật ngữ/tên riêng/"
                    "quan hệ nhân vật đáng nhớ để giữ nhất quán về sau, mỗi dòng một mục theo "
                    "đúng định dạng: TERM | TRANSLATION | NOTE (NOTE có thể để trống). "
                    "Nếu không có gì đáng nhớ, trả lời một dòng trống."
                ),
            },
            {
                "role": "user",
                "content": f"Văn bản gốc:\n{source_text}\n\nBản dịch:\n{translated_text}",
            },
        ]
        response = provider.complete(messages)
        candidates = []
        for line in response.splitlines():
            parts = line.split("|")
            if len(parts) != 3:
                continue
            term, translation, note = (p.strip() for p in parts)
            if not term or not translation:
                continue
            candidates.append((term, translation, note))
        return candidates

    def _resolve_conflict(self, provider, existing, term, new_translation, new_note):
        messages = [
            {
                "role": "system",
                "content": (
                    "Có một xung đột thuật ngữ dịch thuật. Thuật ngữ đã xác lập trước đó và "
                    "cách dùng mới trong chương hiện tại khác nhau. Trả lời đúng một trong hai: "
                    f"'{_CONFLICT_KEEP_OLD}' (giữ bản đã xác lập) hoặc "
                    f"'{_CONFLICT_USE_NEW}: <lý do>' (dùng bản mới)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Thuật ngữ: {term}\n"
                    f"Đã xác lập trước đó: {existing.translation} ({existing.note})\n"
                    f"Cách dùng mới trong chương này: {new_translation} ({new_note})"
                ),
            },
        ]
        response = provider.complete(messages).strip()
        if response.upper().startswith(_CONFLICT_USE_NEW):
            return _CONFLICT_USE_NEW
        return _CONFLICT_KEEP_OLD


@register_node("EvaluateAndFixChapters")
class EvaluateAndFixChapters(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("report",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "agent_instructions": ("STRING", {"default": ""}),
            },
            "optional": {
                "glossary_entries": ("GLOSSARY_ENTRIES", {}),
                "chapter_count": ("STRING", {"default": "5"}),
            },
        }

    def execute(
        self, workspace_name, provider, agent_instructions, glossary_entries=None, chapter_count="5"
    ) -> tuple:
        chapters_path = workspace.get_workspace_path(workspace_name, "chapters.json")
        records = get_recent(load_chapters(chapters_path), int(chapter_count))

        if not records:
            return ("Không có chương nào để đánh giá.",)

        glossary_entries = glossary_entries or []
        fixed = []
        skipped = []

        for record in records:
            try:
                source_text = Path(record.source_path).read_text(encoding="utf-8")
                translated_text = Path(record.output_path).read_text(encoding="utf-8")
            except OSError as exc:
                skipped.append(f"{record.chapter_id}: bỏ qua (không đọc được file: {exc})")
                continue

            relevant = find_relevant_entries(glossary_entries, source_text)
            verdict, description = self._critique(
                provider, agent_instructions, relevant, source_text, translated_text
            )

            if verdict == "LỖI":
                corrected = translate_chunk(provider, agent_instructions, relevant, source_text)
                if not corrected.strip():
                    skipped.append(f"{record.chapter_id}: bỏ qua sửa (LLM trả về rỗng)")
                    continue
                Path(record.output_path).write_text(corrected, encoding="utf-8")
                fixed.append(f"{record.chapter_id}: {description}")

        lines = [f"Đã kiểm tra {len(records)} chương."]
        lines.extend(f"Sửa {entry}" for entry in fixed)
        lines.extend(skipped)
        return ("\n".join(lines),)

    def _critique(self, provider, agent_instructions, relevant_entries, source_text, translated_text):
        system_prompt = agent_instructions
        if relevant_entries:
            entries_text = "\n".join(
                f"- {e.term} → {e.translation}" + (f" ({e.note})" if e.note else "")
                for e in relevant_entries
            )
            system_prompt += "\n\n## Thuật ngữ/quan hệ đã xác lập (giữ nhất quán):\n" + entries_text
        system_prompt += (
            "\n\nSo sánh bản gốc và bản dịch dưới đây. Nếu bản dịch đúng, trả lời đúng "
            "một dòng 'OK'. Nếu có lỗi, trả lời 'LỖI: <mô tả ngắn>'."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Bản gốc:\n{source_text}\n\nBản dịch:\n{translated_text}"},
        ]
        response = provider.complete(messages).strip()
        if response.upper().startswith("LỖI"):
            description = response.split(":", 1)[1].strip() if ":" in response else response
            return ("LỖI", description)
        return ("OK", "")
