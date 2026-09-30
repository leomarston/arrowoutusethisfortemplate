"""Tests for tools/game.py (config, generate, doctor, new).

    python3 -m unittest discover -s tools/tests          # from the repo root
    python3 -m unittest tools.tests.test_game -v

The unit tests build tiny game folders in a temp dir. Two integration tests read apps/mazeout (the reference game):
its game.yml must be valid and `generate` must have nothing to change; `new` on a temp copy must leave only the
expected TODOs (store texts, rendered art, app icon).
"""
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
import game as G  # noqa: E402

REF = "mazeout"


def ref_cfg():
    return G.load_game(REPO, REF)


class JSONSpansTest(unittest.TestCase):
    TEXT = textwrap.dedent("""\
        {
          "unlocks": { "a": 30, "b": 33 },
          "events": {
            "rotation": {
              "enabled": true,
              "seed": "0x524F544154494F4E",
              "always": ["a", "b"],
              "p": -1.5e3
            }
          },
          "list": [ {"x": "q\\"uote"}, null ]
        }
        """)

    def test_every_value_has_its_span(self):
        sp = G.json_spans(self.TEXT)
        get = lambda p: json.loads(self.TEXT[slice(*sp[p])])  # noqa: E731
        self.assertEqual(get(("unlocks", "b")), 33)
        self.assertEqual(get(("events", "rotation", "enabled")), True)
        self.assertEqual(get(("events", "rotation", "always")), ["a", "b"])
        self.assertEqual(get(("events", "rotation", "p")), -1500.0)
        self.assertEqual(get(("list", 0, "x")), 'q"uote')
        self.assertIsNone(get(("list", 1)))
        self.assertEqual(json.loads(self.TEXT), get(()))

    def test_replacing_one_value_keeps_the_rest_byte_identical(self):
        cfg = {"v": ["b", "a", "c"]}
        a = G.Anchor("events", "always", "x.json", path=("events", "rotation", "always"), expect=lambda c: c["v"])
        out = a.apply(self.TEXT, cfg)
        self.assertIn('"always": ["b", "a", "c"],', out)
        self.assertEqual(out.replace('["b", "a", "c"]', '["a", "b"]'), self.TEXT)
        self.assertEqual(a.apply(out, cfg), out)  # idempotent

    def test_bad_json_raises(self):
        with self.assertRaises(G.JSONSpanError):
            G.json_spans('{"a": 1,}')
        with self.assertRaises(G.JSONSpanError):
            G.json_spans('{"a": 1} x')


class ValidateTest(unittest.TestCase):
    def test_reference_game_yml_is_valid(self):
        self.assertEqual(G.validate(ref_cfg(), REF), [])

    def test_bad_values_are_reported(self):
        c = copy.deepcopy(ref_cfg())
        c["identity"]["bundle_id"] = "arrowout"
        c["identity"]["team_id"] = "abc"
        c["store"]["privacy_url"] = "http://x"
        c["events"]["rotation"]["race"] = ["nope"]
        c["features"]["ipad"] = "no"
        del c["store"]["copyright"]
        probs = "\n".join(G.validate(c, "other"))
        for needle in ("identity.bundle_id", "identity.team_id", "store.privacy_url", "'nope' is not in events.unlocks",
                       "features.ipad", "store.copyright: missing", "folder is apps/other"):
            self.assertIn(needle, probs)

    def test_bool_is_not_an_int(self):
        c = copy.deepcopy(ref_cfg())
        c["features"]["rating_after_level"] = True
        self.assertTrue(any("rating_after_level" in p for p in G.validate(c)))


class HelpersTest(unittest.TestCase):
    def test_names(self):
        self.assertEqual(G.camel("Test Game!"), "TestGame")
        self.assertEqual(G.camel("2048 blocks"), "Game2048Blocks")
        self.assertEqual(G.kebab("Arrow Out"), "arrow-out")
        c = ref_cfg()
        self.assertEqual(G.iap_prefix(c), "com.manycode.arrowout.")
        self.assertEqual(G.sku_prefix(c), "arrowout")
        self.assertEqual(G.brands_list(c)[-2:], ["Arrow Out", "ArrowOut"])

    def test_rename_tokens_respects_boundaries(self):
        old = {"slug": "mazeout", "bundle": "com.manycode.arrowout", "product": "ArrowOut", "brand": "Arrow Out",
               "bans": ["Maze", "MazeOut"]}
        new = {"slug": "tg", "bundle": "com.manycode.tg", "product": "TestGame", "brand": "Test Game"}
        src = ('@testable import ArrowOut\nlet q = "com.manycode.arrowout.audio"; let o = "com.manycode.arrowout2"\n'
               'target ArrowOutTests, app ArrowOut.app, art logoArrowOut, ArrowOuts\n'
               'path apps/mazeout/tools apps/mazeout2\n"Arrow Out" "Arrow Outs" sku arrowout- x.arrowout\n'
               'ban MazeOut\n')
        out = G.rename_tokens(src, old, new)
        self.assertIn("@testable import TestGame", out)
        self.assertIn('"com.manycode.tg.audio"', out)
        self.assertIn('"com.manycode.arrowout2"', out)          # another id that only starts the same
        self.assertIn("TestGameTests, app TestGame.app, art logoArrowOut, ArrowOuts", out)
        self.assertIn("apps/tg/tools apps/mazeout2", out)
        self.assertIn('"Test Game" "Arrow Outs" sku tg-', out)
        self.assertIn("ban MazeOut", out)                          # the original's names are never renamed

    def test_yml_edits_keep_comments(self):
        t = "a:\n  name: \"X\"   # the name\n  list:  # items\n    # note\n    - one\n    - two\nb: 1\n"
        t2 = G.yml_set(t, "name", '"Y: z"')
        self.assertIn('  name: "Y: z"   # the name\n', t2)
        t3 = G.yml_set_list(t2, "list", ["three"], indent="    ")
        self.assertIn("  list:  # items\n    # note\n    - three\nb: 1", t3)
        t4 = G.yml_set_list(t2, "list", [], indent="    ")
        self.assertIn("  list: [] # items\n    # note\nb: 1", t4)
        with self.assertRaises(G.ConfigError):
            G.yml_set(t, "missing", "1")


def make_fixture_game(root: Path, slug="fx", bundle="com.acme.fx", product="Fx", brand="Fx Game"):
    """A minimal game folder: game.yml (the reference's values with a new identity) + a few files that repeat them."""
    c = copy.deepcopy(ref_cfg())
    c["id"] = slug
    c["identity"].update(bundle_id=bundle, product=product, brand_name=brand, profile_name="acme fx appstore")
    c["puzzle"]["checks"] = []
    g = root / "apps" / slug
    (g / "fastlane").mkdir(parents=True)
    (g / "App/Resources/Tuning").mkdir(parents=True)
    (g / "App/Support").mkdir(parents=True)
    (g / "game.yml").write_text(G.yaml.safe_dump(c, sort_keys=False))
    (g / "project.yml").write_text(textwrap.dedent(f"""\
        name: {product}
        options:
          bundleIdPrefix: com.acme
        settings:
          base:
            DEVELOPMENT_TEAM: GDU77F3MXL
            PC_BRAND_NAME: "{brand}"                  # the one source
        targets:
          Fx:
            settings:
              base:
                PRODUCT_BUNDLE_IDENTIFIER: {bundle}
                TARGETED_DEVICE_FAMILY: "1"
          FxTests:
            settings: {{ base: {{ PRODUCT_BUNDLE_IDENTIFIER: {bundle}.tests }} }}
          FxUITests:
            settings:
              base:
                PRODUCT_BUNDLE_IDENTIFIER: {bundle}.uitests
        """))
    (g / "fastlane/Appfile").write_text(f'app_identifier "{bundle}"\n')
    (g / "App/Support/Log.swift").write_text(f'let subsystem = "{bundle}"  // {brand} log\n'
                                             f'let q = DispatchQueue(label: "{bundle}.audio")\n')
    (g / "App/Resources/Tuning/game.json").write_text(
        '{\n  "rating": { "afterLevel": 34 },\n  "notifications": {\n    "askOnFirstLaunch": true\n  },\n'
        '  "support": { "email": "anycodeapps@gmail.com" }\n}\n')
    return g, c


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.g, self.c = make_fixture_game(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_cfg(self, c):
        (self.g / "game.yml").write_text(G.yaml.safe_dump(c, sort_keys=False))

    def test_matching_game_needs_nothing(self):
        self.assertEqual(G.plan_generate(self.tmp, "fx"), {})

    def test_new_identity_is_written_and_generate_is_idempotent(self):
        c = copy.deepcopy(self.c)
        c["identity"].update(bundle_id="com.acme.other", team_id="ABCDE12345", brand_name="Other")
        c["features"].update(ipad=True, rating_after_level=40)
        self.write_cfg(c)
        out = io.StringIO()
        self.assertEqual(G.generate(self.tmp, "fx", check=True, out=out), 1)
        self.assertIn("would change project.yml", out.getvalue())
        self.assertEqual((self.g / "fastlane/Appfile").read_text(), 'app_identifier "com.acme.fx"\n')  # --check wrote nothing
        self.assertEqual(G.generate(self.tmp, "fx", check=False, out=io.StringIO()), 0)
        py = (self.g / "project.yml").read_text()
        for s in ("PRODUCT_BUNDLE_IDENTIFIER: com.acme.other\n", "com.acme.other.tests }", "com.acme.other.uitests\n",
                  "DEVELOPMENT_TEAM: ABCDE12345", 'PC_BRAND_NAME: "Other"                  # the one source',
                  'TARGETED_DEVICE_FAMILY: "1,2"', "name: Fx\n"):
            self.assertIn(s, py)
        self.assertEqual((self.g / "fastlane/Appfile").read_text(), 'app_identifier "com.acme.other"\n')
        log = (self.g / "App/Support/Log.swift").read_text()
        self.assertIn('"com.acme.other.audio"', log)
        self.assertIn("// Other log", log)
        gj = json.loads((self.g / "App/Resources/Tuning/game.json").read_text())
        self.assertEqual(gj["rating"]["afterLevel"], 40)
        self.assertIn('"rating": { "afterLevel": 40 }', (self.g / "App/Resources/Tuning/game.json").read_text())
        self.assertEqual(G.plan_generate(self.tmp, "fx"), {})

    def test_invalid_config_refuses_to_generate(self):
        c = copy.deepcopy(self.c)
        c["identity"]["team_id"] = "x"
        self.write_cfg(c)
        with self.assertRaises(G.ConfigError):
            G.plan_generate(self.tmp, "fx")

    def test_doctor_flags_a_mismatch_and_another_games_leftover(self):
        (self.g / "fastlane/Appfile").write_text('app_identifier "com.acme.wrong"\n')
        make_fixture_game(self.tmp, slug="gx", bundle="com.acme.gx", product="Gx", brand="Gx Game")
        (self.g / "App/Support/Extra.swift").write_text('let x = "com.acme.gx.save"\n')
        R = G.doctor(self.tmp, "fx", quick=True)
        fails = {(i[2], i[3]) for i in R.items if i[0] == G.FAIL}
        self.assertTrue(any(lbl == "Appfile app_identifier" and "com.acme.wrong" in d for lbl, d in fails), fails)
        self.assertTrue(any(lbl == "leftover bundle id of apps/gx" for lbl, _ in fails), fails)
        self.assertTrue(any("literals are this bundle" in lbl for lbl, _ in fails), fails)

    def test_doctor_schema_failure_stops_early(self):
        c = copy.deepcopy(self.c)
        c["schema"] = 99
        self.write_cfg(c)
        R = G.doctor(self.tmp, "fx")
        self.assertEqual([i[2] for i in R.items], ["schema"])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(G.main(["--repo", str(self.tmp), "doctor", "--game", "fx"]), 2)
        self.assertIn("[FAIL] schema", out.getvalue())


class ReferenceGameTest(unittest.TestCase):
    """apps/mazeout is the regression fixture: its files agree with its game.yml."""

    def test_generate_has_nothing_to_change(self):
        plan = G.plan_generate(REPO, REF)
        self.assertEqual({p.relative_to(REPO).as_posix(): n for p, (_, _, n) in plan.items()}, {})

    def test_every_anchor_is_found(self):
        gdir = G.game_dir(REPO, REF)
        cfg = ref_cfg()
        bad = [(a.key, d) for a in G.anchors(cfg) for st, d in [a.check(gdir, cfg)] if st in (G.FAIL, G.WARN)]
        self.assertEqual(bad, [])


@unittest.skipUnless(os.environ.get("GAME_PY_SLOW", "1") == "1", "GAME_PY_SLOW=0")
class NewGameTest(unittest.TestCase):
    """`new` on a temp copy of apps/mazeout: doctor lists only the expected TODOs."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        src = REPO / "apps" / REF
        shutil.copytree(src, cls.tmp / "apps" / REF,
                        ignore=shutil.ignore_patterns("research", "build", "__pycache__", "*.xcodeproj", ".build"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_new_same_puzzle(self):
        G.new_game(self.tmp, "tg", REF, "Test Game", "com.manycode.tg", out=io.StringIO())
        g = self.tmp / "apps/tg"
        self.assertTrue((g / "App/Resources/StoreKit/TestGame.storekit").exists())
        self.assertFalse((g / "App/Resources/StoreKit/ArrowOut.storekit").exists())
        self.assertFalse((g / "research").exists())
        self.assertFalse((g / "fastlane/screenshots").exists())
        self.assertFalse((g / "art/out").exists())
        self.assertTrue((g / "design/levels.json").exists())
        cfg = G.load_game(self.tmp, "tg")
        self.assertEqual(cfg["derived_from"], REF)
        self.assertEqual(cfg["identity"]["product"], "TestGame")
        self.assertEqual(cfg["identity"]["profile_name"], "manycode tg appstore")
        self.assertEqual(G.plan_generate(self.tmp, "tg"), {})
        R = G.doctor(self.tmp, "tg", quick=True)
        fails = sorted(i[2] for i in R.items if i[0] == G.FAIL)
        self.assertEqual(fails, ["app icon", "shipped art files", "store texts"], R.render("doctor"))
        warns = sorted(i[2] for i in R.items if i[0] == G.WARN)
        self.assertIn("levels are this game's own", warns)
        self.assertIn("strings coverage sources (tools/strings/sources.json)", warns)   # the reference's SPEC docs
        # the reference is unaffected by its copy
        ref_fails = [i for i in G.doctor(self.tmp, REF, quick=True).items if i[0] == G.FAIL]
        self.assertEqual(ref_fails, [])

    def test_new_other_puzzle_with_bans(self):
        G.new_game(self.tmp, "sorty", REF, "Sorty", "com.manycode.sorty", puzzle="sort-stack",
                   bans=["Sort Legend", "sortlegend"], out=io.StringIO())
        g = self.tmp / "apps/sorty"
        self.assertEqual([p.name for p in (g / "App/Resources/Levels").iterdir()], [".gitkeep"])
        self.assertFalse((g / "design/levels.json").exists())
        cfg = G.load_game(self.tmp, "sorty")
        self.assertEqual(cfg["puzzle"]["module"], "sort-stack")
        self.assertEqual(cfg["puzzle"]["checks"], [])
        self.assertEqual(cfg["brand_bans"], ["Sort Legend", "sortlegend"])
        self.assertIn('"Sort Legend", "sortlegend", "Sorty"',
                      (g / "tools/strings/build.py").read_text())
        R = G.doctor(self.tmp, "sorty", quick=True)
        fails = sorted(i[2] for i in R.items if i[0] == G.FAIL)
        # the store-text gate (loc.py BANNED_ALL, hand-kept) must learn the new original's names: a real TODO
        self.assertEqual(fails, ["app icon", "levels", "shipped art files",
                                 "store texts", "store-text gate (loc.py BANNED_ALL) catches every ban"],
                         R.render("doctor"))

    def test_new_refuses_bad_input(self):
        with self.assertRaises(G.ConfigError):
            G.new_game(self.tmp, "Bad Slug", REF, "X", "com.a.b", out=io.StringIO())
        with self.assertRaises(G.ConfigError):
            G.new_game(self.tmp, "ok", REF, "X", "nodots", out=io.StringIO())
        with self.assertRaises(G.ConfigError):
            G.new_game(self.tmp, REF, REF, "X", "com.a.b", out=io.StringIO())


if __name__ == "__main__":
    unittest.main()
