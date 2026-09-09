from ai.evaluation.run_eval import accuracy, evaluate


def test_perfect_accuracy():
    y = ["happy", "sad", "neutral"]
    assert accuracy(y, y) == 1.0


def test_evaluate_keys():
    result = evaluate(["happy", "sad"], ["happy", "neutral"])
    assert "accuracy" in result
    assert "confusion_matrix" in result
    assert "per_class" in result
