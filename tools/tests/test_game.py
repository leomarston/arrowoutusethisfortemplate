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


class BanFormsTest(unittest.TestCase):
    """The derived ban lists reproduce the reference's hand-written ones exactly (BrandTests, release_gates.sh gate 3)."""

    def test_words_split_spaces_and_camel_humps(self):
        self.assertEqual(G.ban_words("MazeOut"), ["maze", "out"])
        self.assertEqual(G.ban_words("Arrow Jam"), ["arrow", "jam"])
        self.assertEqual(G.ban_words("grandgames"), ["grandgames"])
        self.assertEqual(G.ban_words("ABC Games"), ["abc", "games"])

    def test_reference_phrases_and_exact_rest(self):
        c = ref_cfg()
        self.assertEqual(G.ban_phrases(c), ["mazeout", "maze out", "arrowjam", "arrow jam", "grandgames", "grand games"])
        self.assertEqual(G.ban_exact_rest(c), ["Maze"])
        self.assertEqual(G.ban_exact_rest({"brand_bans": ["Sort Legend"]}), ["Sort Legend"])   # never empty

    def test_alternation_compares_as_a_set(self):
        self.assertEqual(G._alt_set("a\\|b"), G._alt_set("b\\|a"))
        self.assertNotEqual(G._alt_set("a\\|b"), G._alt_set("a"))

    def test_wrapped_raw_list_round_trips(self):
        pats = [r"maze", r"grand\s*games", r"\bjam\b", "迷路"] * 9
        text = G._py_raw_list_wrapped(pats)
        self.assertTrue(all(len(line) <= 120 for line in text.splitlines()))
        self.assertEqual(eval(text), pats)  # noqa: S307 - our own rendered literal

    def test_bad_ban_forms_are_reported(self):
        c = copy.deepcopy(ref_cfg())
        c["brand_ban_forms"]["store_patterns"] = ["ok", "bad(", 'quo"te']
        c["brand_ban_forms"]["binary_words"] = []
        c["brand_ban_forms"]["file_stems"] = ["Upper"]
        probs = " ".join(G.validate(c, REF))
        for k in ("brand_ban_forms.store_patterns", "brand_ban_forms.binary_words", "brand_ban_forms.file_stems"):
            self.assertIn(k, probs)


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


GATES_SNIPPET = textwrap.dedent("""\
    names=$(find "$REL" -mindepth 1 | sed "s|^$REL/||" | grep -i "maze\\|grand\\|arrowjam" | wc -l | tr -d ' ')
    echo "  file names with maze/grand/arrowjam: $names (must be 0)"
      if grep -qi "mazeout\\|maze out\\|arrow jam\\|arrowjam\\|grand games\\|grandgames" "$TMP/one.txt" || grep -q "Maze" "$TMP/one.txt"; then
    WORDS = re.compile(rb'(?i)maze|recorded|video|research/|v552|v582|bot_time')
    NEVER_SDK = re.compile(rb'(?i)maze|research/|v552|v582|bot_time')     # never excused
    """)


def add_core_and_gates(g: Path, c: dict):
    """The fixture game + a GameCore folder (generate owns its GameConfig) + the ban lists' files, all fresh."""
    (g / "Packages/Core/Sources/GameCore/Social").mkdir(parents=True)
    (g / "Packages/Core/Sources/GameCore/Social/World.swift").write_text(
        "enum World { static let seed = GameConfig.worldSeed }\n")
    (g / "tools/release").mkdir(parents=True)
    (g / "tools/strings").mkdir(parents=True)
    (g / "tools/bench").mkdir(parents=True)
    (g / "tools/release/loc.py").write_text("BANNED_BRAND = []\nBANNED_ALL = BANNED_BRAND + [r\"online\"]\n")
    (g / "tools/strings/l10n_review.py").write_text('BRAND_RE = re.compile(r"x", re.I)\n')
    (g / "tools/bench/release_gates.sh").write_text(GATES_SNIPPET)
    for p, (_, new, _) in G.plan_generate(g.parents[1], c["id"], c).items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new, encoding="utf-8")


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

    def test_core_config_is_generated_and_checked_fresh(self):
        add_core_and_gates(self.g, self.c)
        gen = self.g / "Packages/Core/Sources/GameCore/Config/GameConfig.generated.swift"
        text = gen.read_text()
        for s in ("public static let worldSeed: UInt64 = 0x4152_4F57_204F_5554",
                  "public static let worldEpoch: Int = 1_788_764_400",
                  "public static let calendarEpoch: Int = 1_777_273_200",
                  'public static let rotationSeed: String = "0x524F544154494F4E"',
                  "public static let rotationSeedValue: UInt64 = 0x524F_5441_5449_4F4E",
                  'public static let productPrefix: String = "com.acme.fx."'):
            self.assertIn(s, text)
        self.assertNotIn(self.c["identity"]["brand_name"], text)       # CI's brand check greps the core's sources
        self.assertEqual(G.plan_generate(self.tmp, "fx"), {})
        label = "GameConfig.generated.swift (world seed + epochs, rotation seed, IAP prefix)"

        def status(lbl):
            return [i[0] for i in G.doctor(self.tmp, "fx", quick=True).items if i[2] == lbl]
        self.assertEqual(status(label), [G.PASS])
        self.assertEqual(status("no game.yml value spelled in the Swift sources (only GameConfig)"), [G.PASS])
        # a hand edit is stale; a new seed in game.yml is written by generate (and the old value is gone)
        gen.write_text(text.replace("0x4152_4F57_204F_5554", "0x0000_0000_0000_0001"))
        self.assertEqual(status(label), [G.FAIL])
        c = copy.deepcopy(self.c)
        c["social"]["world_seed"] = "0x00000000DEADBEEF"
        self.write_cfg(c)
        out = io.StringIO()
        self.assertEqual(G.generate(self.tmp, "fx", check=False, out=out), 0)
        self.assertIn("worldSeed: UInt64 = 0x0000_0000_DEAD_BEEF", gen.read_text())
        self.assertEqual(status(label), [G.PASS])
        # a missing file is written again
        gen.unlink()
        self.assertEqual(status(label), [G.FAIL])
        self.assertEqual(G.generate(self.tmp, "fx", check=False, out=io.StringIO()), 0)
        self.assertTrue(gen.exists())

    def test_a_value_spelled_in_swift_fails(self):
        add_core_and_gates(self.g, self.c)
        core = self.g / "Packages/Core/Sources/GameCore"
        (core / "Social/Old.swift").write_text("let s: UInt64 = 0x4152_4f57_204f_5554\nlet e = 1_777_273_200\n")
        (self.g / "App/Support/Shop.swift").write_text('let p = "com.acme.fx."\nlet q = "com.acme.fx.save"\n')
        hits = G.mirrored_literals(self.g, self.c)
        self.assertEqual(sorted(hits), sorted([
            ("Packages/Core/Sources/GameCore/Social/Old.swift", "0x4152_4f57_204f_5554"),
            ("Packages/Core/Sources/GameCore/Social/Old.swift", "1_777_273_200"),
            ("App/Support/Shop.swift", '"com.acme.fx."')]))
        R = G.doctor(self.tmp, "fx", quick=True)
        self.assertIn((G.FAIL, "no game.yml value spelled in the Swift sources (only GameConfig)"),
                      [(i[0], i[2]) for i in R.items])

    def test_ban_lists_are_generated_from_game_yml(self):
        add_core_and_gates(self.g, self.c)
        gates = (self.g / "tools/bench/release_gates.sh").read_text()
        self.assertEqual(gates, GATES_SNIPPET, "the reference's lines are already what generate writes (data files: a set)")
        loc = (self.g / "tools/release/loc.py").read_text()
        self.assertIn('BANNED_BRAND = [\n    r"maze", r"mazeout", r"grand\\s*games",', loc)
        self.assertIn('BRAND_RE = re.compile(r"\\bmaze\\s*out|\\bmazeout|grand\\s*games|arrow\\s*jam|tap\\s*away|tapaway|v552", re.I)',
                      (self.g / "tools/strings/l10n_review.py").read_text())
        # a new original: every list follows game.yml
        c = copy.deepcopy(self.c)
        c["brand_bans"] = ["Sort Legend", "sortlegend", "Tubes"]
        c["brand_ban_forms"] = {"store_patterns": [r"sort\s*legend", r"tubes?"], "file_stems": ["sortlegend", "tube"],
                                "binary_words": ["sortlegend"], "review_patterns": [r"sort\s*legend"]}
        self.write_cfg(c)
        self.assertEqual(G.generate(self.tmp, "fx", check=False, out=io.StringIO()), 0)
        gates = (self.g / "tools/bench/release_gates.sh").read_text()
        self.assertIn('grep -i "sortlegend\\|tube" | wc -l', gates)
        self.assertIn('file names with sortlegend/tube: $names', gates)
        self.assertIn('grep -qi "sortlegend\\|sort legend" "$TMP/one.txt" || grep -q "Tubes" "$TMP/one.txt"; then', gates)
        self.assertIn("WORDS = re.compile(rb'(?i)sortlegend|recorded|video|", gates)
        self.assertIn("NEVER_SDK = re.compile(rb'(?i)sortlegend|research/", gates)
        loc = (self.g / "tools/release/loc.py").read_text()
        self.assertIn('BANNED_BRAND = [\n    r"sort\\s*legend", r"tubes?",\n]\nBANNED_ALL = BANNED_BRAND + [r"online"]', loc)
        self.assertIn('BRAND_RE = re.compile(r"sort\\s*legend", re.I)', (self.g / "tools/strings/l10n_review.py").read_text())
        self.assertEqual(G.plan_generate(self.tmp, "fx"), {})
        R = G.doctor(self.tmp, "fx", quick=True)
        brand = {i[2]: i[0] for i in R.items if i[1] == "8. Brand bans"}
        for lbl in ("store-text gate (brand_ban_forms.store_patterns) catches every ban",
                    "gate 3 file names (brand_ban_forms.file_stems) catch every ban",
                    "l10n review (brand_ban_forms.review_patterns) catches every ban phrase"):
            self.assertEqual(brand[lbl], G.PASS, lbl)
        # a list that misses a ban is a FAIL (the gate would let the name through)
        c["brand_ban_forms"]["file_stems"] = ["sortlegend"]
        c["brand_ban_forms"]["review_patterns"] = ["tubes"]
        self.write_cfg(c)
        R = G.doctor(self.tmp, "fx", quick=True)
        fails = {i[2] for i in R.items if i[0] == G.FAIL}
        self.assertIn("gate 3 file names (brand_ban_forms.file_stems) catch every ban", fails)
        self.assertIn("l10n review (brand_ban_forms.review_patterns) catches every ban phrase", fails)

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

    def test_core_config_keeps_the_shipped_values(self):
        """The world is deterministic from these: the generated constants are the literals the core had before they
        moved to game.yml, character for character (the frozen goldens depend on them)."""
        gdir = G.game_dir(REPO, REF)
        [(p, want, _)] = G.generated_files(gdir, ref_cfg())
        self.assertEqual(p.relative_to(gdir).as_posix(), "Packages/PathCore/Sources/GameCore/Config/GameConfig.generated.swift")
        self.assertEqual(p.read_text(encoding="utf-8"), want)
        for s in ("worldSeed: UInt64 = 0x4152_4F57_204F_5554", "worldEpoch: Int = 1_788_764_400",
                  "calendarEpoch: Int = 1_777_273_200", 'rotationSeed: String = "0x524F544154494F4E"',
                  "rotationSeedValue: UInt64 = 0x524F_5441_5449_4F4E", 'productPrefix: String = "com.manycode.arrowout."'):
            self.assertIn(s, want)
        self.assertEqual(G.mirrored_literals(gdir, ref_cfg()), [])


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
        # the gates' other ban forms (game.yml brand_ban_forms, kept from the reference) must learn the new original's
        # names: real TODOs (generate then writes them into loc.py, release_gates.sh and l10n_review.py)
        self.assertEqual(fails, ["app icon", "gate 3 file names (brand_ban_forms.file_stems) catch every ban",
                                 "l10n review (brand_ban_forms.review_patterns) catches every ban phrase", "levels",
                                 "shipped art files", "store texts",
                                 "store-text gate (brand_ban_forms.store_patterns) catches every ban"],
                         R.render("doctor"))
        # the core's constants follow the new bundle id (generate wrote GameConfig)
        gen = (g / "Packages/PathCore/Sources/GameCore/Config/GameConfig.generated.swift").read_text()
        self.assertIn('productPrefix: String = "com.manycode.sorty."', gen)

    def test_new_refuses_bad_input(self):
        with self.assertRaises(G.ConfigError):
            G.new_game(self.tmp, "Bad Slug", REF, "X", "com.a.b", out=io.StringIO())
        with self.assertRaises(G.ConfigError):
            G.new_game(self.tmp, "ok", REF, "X", "nodots", out=io.StringIO())
        with self.assertRaises(G.ConfigError):
            G.new_game(self.tmp, REF, REF, "X", "com.a.b", out=io.StringIO())


if __name__ == "__main__":
    unittest.main()
