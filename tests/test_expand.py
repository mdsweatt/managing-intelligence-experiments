from harness.config import load_run_matrix, load_manifest
from harness.expand import resolve_hypothesis_config, resolve_swapped_config, expand_matrix, family_for, skipped_bands

RM = load_run_matrix("runs/phase1a.yaml")
MODELS = RM.models
TASKS = {t.id: t for t in RM.tasks}
MANIFEST = load_manifest("fixtures/manifest.yaml")

def test_hypothesis_config_sonnet_is_high_no_thinking():
    cfg = resolve_hypothesis_config(TASKS[6], "S", MODELS)  # short_form_copy, sonnet
    assert (cfg.model_role, cfg.effort, cfg.thinking) == ("sonnet", "high", "off")
    assert cfg.temperature == "omitted"
    assert cfg.max_tokens == MODELS["sonnet"].max_output

def test_hypothesis_config_haiku_has_no_effort():
    cfg = resolve_hypothesis_config(TASKS[1], "S", MODELS)  # draft_email, haiku
    assert (cfg.model_role, cfg.effort, cfg.thinking) == ("haiku", None, "off")

def test_hypothesis_config_15_band_is_effort_and_thinks():
    cfg = resolve_hypothesis_config(TASKS[15], "high", MODELS)  # strategy_brief, opus
    assert (cfg.model_role, cfg.effort, cfg.thinking) == ("opus", "high", "adaptive")

def test_swap_from_haiku_is_matched_minimal_floor():
    hypo = resolve_hypothesis_config(TASKS[1], "S", MODELS)   # haiku
    over = resolve_swapped_config(hypo, "opus", MODELS)
    assert (over.model_role, over.effort, over.thinking) == ("opus", "low", "off")
    assert over.max_tokens == MODELS["opus"].max_output

def test_swap_to_haiku_drops_effort():
    hypo = resolve_hypothesis_config(TASKS[6], "S", MODELS)   # sonnet, high
    dp = resolve_swapped_config(hypo, "haiku", MODELS)
    assert (dp.model_role, dp.effort) == ("haiku", None)

def test_swap_sonnet_to_opus_copies_config():
    hypo = resolve_hypothesis_config(TASKS[16], "few", MODELS)  # sonnet, thinking adaptive
    over = resolve_swapped_config(hypo, "opus", MODELS)
    assert (over.model_role, over.effort, over.thinking) == ("opus", "high", "adaptive")

def test_family_classification():
    assert family_for("cached_context") == "cache"
    assert family_for("turns") == "multiturn"
    assert family_for("payload") == "payload"
    assert family_for("input") == "standard"
    assert family_for("output") == "standard"

def test_expand_emits_ladder_per_band():
    units = expand_matrix(RM, MANIFEST)
    # task 6 (sonnet, S, +opus over-service, +haiku down-probe) -> 3 units
    t6 = [u for u in units if u.cell_id.task_id == 6]
    assert {u.role_label for u in t6} == {"hypothesis", "over_service", "down_probe"}
    assert {u.cell_id.model_role for u in t6} == {"sonnet", "opus", "haiku"}
    assert all(u.n == RM.meta.n_per_cell for u in t6)

def test_expand_15_uses_shared_fixture_for_each_effort_band():
    units = expand_matrix(RM, MANIFEST)
    t15 = [u for u in units if u.cell_id.task_id == 15]
    # three effort bands × (opus hyp + sonnet down-probe) = 6 units, all on the 'shared' fixture
    assert {u.cell_id.band for u in t15} == {"low", "high", "max"}
    assert all(u.fixture.band == "shared" for u in t15)

def test_expand_empty_manifest_skips_all_and_reports():
    from harness.config import Manifest
    empty = Manifest(schema_version=2, fixtures=[])
    assert expand_matrix(RM, empty) == []
    expected = [(t.id, b) for t in RM.tasks for b in t.bands]
    assert sorted(skipped_bands(RM, empty)) == sorted(expected)

def test_skipped_bands_lists_deferred_L_not_present_bands():
    sk = skipped_bands(RM, MANIFEST)
    assert (8, "L") in sk            # deferred, no fixture in the manifest
    assert (8, "M") not in sk        # fixture entry present (frozen)
    units = expand_matrix(RM, MANIFEST)
    assert not any(u.cell_id.task_id == 8 and u.cell_id.band == "L" for u in units)
