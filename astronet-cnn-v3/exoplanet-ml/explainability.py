"""
explainability.py — Explainable AI Layer for Signal Classification

Provides feature importance explanation for the signal classifier output.

Strategy:
  - Attempts to use SHAP TreeExplainer if the shap package is installed.
  - If SHAP is unavailable, automatically falls back to RandomForest's
    built-in feature_importances_ attribute.

All explanation outputs are normalised to sum to 100% contribution.
"""

import sys
import io
import numpy as np

# Force UTF-8 encoding for standard streams to prevent Unicode errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Attempt to import SHAP; fall back silently if unavailable
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

EXPLAINABILITY_MODE = 'SHAP' if SHAP_AVAILABLE else 'RandomForest Feature Importance'


def explain(
        features: dict,
        classifier,
        astronet_score: float = 0.0
) -> dict:
    """
    Compute feature importance explanations for the classifier prediction.

    Tries SHAP TreeExplainer first. If SHAP is not available, falls back to
    RandomForest built-in feature importances.

    Args:
        features: Dictionary of extracted astrophysical features.
        classifier: Trained RandomForestClassifier instance from classifier.py.
        astronet_score: AstroNet CNN score used during classification.

    Returns:
        Dictionary with:
            mode: 'SHAP' or 'RandomForest Feature Importance'.
            contributions: {feature_name: contribution_percentage} sorted desc.
            top_features: List of (feature_name, contribution_pct) top-5 pairs.
    """
    from classifier import FEATURE_NAMES

    feature_vector = np.array([[
        features.get('transit_depth', 0.0),
        features.get('snr', 0.0),
        features.get('orbital_period', 5.0),
        features.get('transit_duration_hours', 2.0),
        float(features.get('n_transits', 1)),
        features.get('odd_even_diff', 0.0),
        features.get('secondary_eclipse_strength', 0.0),
        features.get('transit_shape_score', 0.5),
        features.get('transit_symmetry', 0.5),
        features.get('depth_uncertainty', 0.0),
        float(astronet_score),
    ]])

    if SHAP_AVAILABLE:
        contributions = _explain_shap(classifier, feature_vector, FEATURE_NAMES)
        mode = 'SHAP TreeExplainer'
    else:
        contributions = _explain_rf_importance(classifier, FEATURE_NAMES)
        mode = 'RandomForest Feature Importance'

    top_features = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:5]

    print(f'✅ Explainability ({mode}):')
    for name, pct in top_features:
        print(f'   {name}: {pct:.1f}%')

    return {
        'mode':         mode,
        'contributions': contributions,
        'top_features': [{'feature': n, 'contribution': p} for n, p in top_features],
    }


def _explain_shap(
        classifier,
        feature_vector: np.ndarray,
        feature_names: list
) -> dict:
    """
    Use SHAP TreeExplainer to compute per-feature contributions.

    Returns normalised absolute SHAP values as percentage contributions.
    """
    explainer = shap.TreeExplainer(classifier)
    shap_values = explainer.shap_values(feature_vector)
    # shap_values shape: [n_classes, n_samples, n_features]
    # Sum absolute SHAP values across all classes for a global view
    if isinstance(shap_values, list):
        abs_shap = np.sum([np.abs(sv) for sv in shap_values], axis=0)[0]
    else:
        abs_shap = np.abs(shap_values[0])

    total = np.sum(abs_shap)
    contributions = {
        name: round(float(v / total) * 100, 1) if total > 0 else 0.0
        for name, v in zip(feature_names, abs_shap)
    }
    return dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True))


def _explain_rf_importance(
        classifier,
        feature_names: list
) -> dict:
    """
    Use RandomForest built-in feature importances as fallback.

    Returns normalised importances as percentage contributions.
    """
    importances = classifier.feature_importances_
    total = np.sum(importances)
    contributions = {
        name: round(float(imp / total) * 100, 1) if total > 0 else 0.0
        for name, imp in zip(feature_names, importances)
    }
    return dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True))
