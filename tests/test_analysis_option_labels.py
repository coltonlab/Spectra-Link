from config.techniques import ANALYSIS_OPTION_META


def test_legend_label_uses_sample_label_text():
    assert ANALYSIS_OPTION_META["legend_label"]["label"] == "Sample Label"
