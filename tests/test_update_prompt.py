"""v0.2.33: ao detectar versão nova, pergunta se deseja atualizar."""
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from venus8 import app as app_module
from venus8.app import App as VenusApp


class FakeRoot:
    def __init__(self, grab=None):
        self.grab = grab
        self.scheduled = []

    def grab_current(self):
        return self.grab

    def after(self, ms, fn):
        self.scheduled.append(ms)


def fake_app(release, grab=None):
    win = SimpleNamespace(release=release, updating=False, _update_prompted=None, settings={},
                          root=FakeRoot(grab), installs=0, saves=0)
    win.UPDATE_PROMPT_SNOOZE_SECONDS = VenusApp.UPDATE_PROMPT_SNOOZE_SECONDS
    win.install_update = lambda: setattr(win, "installs", win.installs + 1)
    win._save_settings = lambda: setattr(win, "saves", win.saves + 1)
    win.maybe_prompt_update = lambda rel: VenusApp.maybe_prompt_update(win, rel)
    return win


def dialog_answering(choice):
    """Simula vintage_dialog pressionando o botão escolhido (0 = atualizar, 1 = depois)."""
    calls = []

    def fake(root, title, message, buttons=()):
        calls.append((title, message, [label for label, _ in buttons]))
        command = buttons[choice][1]
        if command:
            command()
    return fake, calls


class UpdatePromptTests(unittest.TestCase):
    def test_yes_starts_the_upd_button_flow_once(self):
        rel = {"tag_name": "v9.9.9"}
        win = fake_app(rel)
        fake, calls = dialog_answering(0)
        with mock.patch.object(app_module, "vintage_dialog", fake):
            win.maybe_prompt_update(rel)
            win.maybe_prompt_update(rel)
        self.assertEqual(len(calls), 1)
        self.assertIn("Deseja atualizar agora?", calls[0][1])
        self.assertEqual(calls[0][2], ["ATUALIZAR AGORA", "DEPOIS"])
        self.assertEqual(win.installs, 1)

    def test_no_snoozes_same_version_for_24_hours(self):
        rel = {"tag_name": "v9.9.9"}
        win = fake_app(rel)
        fake, calls = dialog_answering(1)
        with mock.patch.object(app_module, "vintage_dialog", fake):
            win.maybe_prompt_update(rel)
            self.assertEqual((win.installs, win.saves), (0, 1))
            self.assertEqual(win.settings["update_prompt_snooze"]["version"], "v9.9.9")
            win._update_prompted = None  # nova sessão
            win.maybe_prompt_update(rel)
            self.assertEqual(len(calls), 1)
            win.settings["update_prompt_snooze"]["at"] = time.time() - 25 * 3600
            win.maybe_prompt_update(rel)
            self.assertEqual(len(calls), 2)

    def test_not_over_another_dialog_nor_while_downloading(self):
        rel = {"tag_name": "v9.9.9"}
        win = fake_app(rel, grab=object())
        with mock.patch.object(app_module, "vintage_dialog") as ask:
            win.maybe_prompt_update(rel)
            self.assertEqual(win.root.scheduled, [5000])
            win.root.grab = None
            win.updating = True
            win.maybe_prompt_update(rel)
        ask.assert_not_called()

    def test_check_result_schedules_the_prompt(self):
        source = (app_module.__file__ and open(app_module.__file__, encoding="utf-8").read())
        self.assertIn("self.root.after(300,lambda r=rel:self.maybe_prompt_update(r))", source)


if __name__ == "__main__":
    unittest.main()
