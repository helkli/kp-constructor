"""Тесты хранилища: сериализация разделов при сохранении КП."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.brief import Brief, validate  # noqa: E402
from src.proposal import Proposal, Section  # noqa: E402


def _make_brief(storage) -> int:
    services = storage.list_services(active_only=True)
    brief = Brief(
        client="ООО Тест",
        task="Задача",
        service_ids=[services[0]["id"]],
        deadline="2 недели",
        budget="",
    )
    assert not validate(brief)
    return storage.create_brief(
        brief.client, brief.task, brief.deadline, brief.budget, brief.service_ids
    )


def test_create_proposal_with_section_objects(storage):
    """Регрессия: сохранить КП можно, передав объекты Section (как в редакторе)."""
    brief_id = _make_brief(storage)
    sections = [Section(header="Обращение", body="Здравствуйте!")]

    pid = storage.create_proposal(brief_id, 1, "draft", sections, [])
    saved = storage.get_proposal(pid)

    assert saved["id"] == pid
    assert saved["brief_id"] == brief_id
    assert saved["version"] == 1


def test_create_proposal_roundtrip_sections_and_pricing(storage):
    """Текст разделов и прайс сохраняются и читаются без потерь."""
    brief_id = _make_brief(storage)
    sections = [Section(header="Сроки", body="Срок выполнения работ: 2 недели.")]
    pricing = [{"name": "ИТ-аудит", "price_text": "25 000 ₽"}]

    pid = storage.create_proposal(
        brief_id, 1, "draft", sections, pricing
    )
    saved = storage.get_proposal(pid)

    restored_sections = Proposal.sections_from_json(saved["sections_json"])
    restored_pricing = Proposal.pricing_from_json(saved["pricing_json"])

    assert restored_sections == [
        {"header": "Сроки", "body": "Срок выполнения работ: 2 недели."}
    ]
    assert restored_pricing == pricing


def test_create_proposal_with_dict_sections(storage):
    """Вариант вызова из страницы брифа (словари) продолжает работать."""
    brief_id = _make_brief(storage)
    sections = [{"header": "Обращение", "body": "Здравствуйте!"}]

    pid = storage.create_proposal(brief_id, 1, "draft", sections, [])
    saved = storage.get_proposal(pid)
    assert saved["id"] == pid