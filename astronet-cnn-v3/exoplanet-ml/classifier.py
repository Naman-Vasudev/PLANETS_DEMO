"""
classifier.py — Multi-Class Astrophysical Signal Classifier

Implements a rule-assisted heuristic classifier initialized using astrophysical priors.
The classifier uses a RandomForestClassifier trained on a synthetic dataset
generated from astrophysically motivated decision rules.

The five signal classes are:
  0: Exoplanet Transit
  1: Eclipsing Binary
  2: Blend / Contaminated Source
  3: Variable Star
  4: False Positive / Noise

The AstroNet CNN score (when available) is incorporated as a supplementary feature
alongside BLS-derived features, ensuring AstroNet contributes to the final vetting
rather than operating after classification.
"""

import sys
import io
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# Force UTF-8 encoding for standard streams to prevent Unicode errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Class label definitions
SIGNAL_CLASSES = [
    'Exoplanet Transit',
    'Eclipsing Binary',
    'Blend / Contaminated Source',
    'Variable Star',
    'False Positive / Noise',
]

# Feature column order (must match the order used when calling classify())
FEATURE_NAMES = [
    'transit_depth',
    'snr',
    'orbital_period',
    'transit_duration_hours',
    'n_transits',
    'odd_even_diff',
    'secondary_eclipse_strength',
    'transit_shape_score',
    'transit_symmetry',
    'depth_uncertainty',
    'astronet_score',  # AstroNet CNN prediction (0-1); 0 if unavailable
]

# Singleton model and encoder instances
_model: RandomForestClassifier | None = None
_encoder: LabelEncoder | None = None


def _generate_training_data(n_samples_per_class: int = 500,
                            seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a rule-assisted training dataset using astrophysical priors.

    Each class is characterised by its expected astrophysical behaviour:
      - Exoplanet Transit: moderate depth, high SNR, U-shape, symmetric,
                           low odd-even diff, no secondary eclipse,
                           high AstroNet score.
      - Eclipsing Binary:  large depth OR large odd-even diff, V-shape,
                           strong secondary eclipse, low AstroNet score.
      - Blend / Contaminated: shallow depth, low SNR, moderate secondary.
      - Variable Star:     very low depth, low period, very low SNR.
      - False Positive / Noise: SNR < 4, near-zero depth.

    Returns:
        X: Feature matrix of shape (n_total_samples, n_features).
        y: Integer label array.
    """
    rng = np.random.default_rng(seed)
    X_parts = []
    y_parts = []

    def clip(arr, lo, hi):
        return np.clip(arr, lo, hi)

    n = n_samples_per_class

    # Class 0: Exoplanet Transit
    X0 = np.column_stack([
        clip(rng.normal(0.005, 0.003, n), 0.0005, 0.05),    # transit_depth: ~0.1-5%
        clip(rng.normal(15.0, 5.0, n), 7.0, 60.0),          # snr: >7
        clip(rng.normal(5.0, 3.0, n), 0.5, 30.0),           # orbital_period
        clip(rng.normal(2.5, 1.0, n), 0.5, 10.0),           # transit_duration_hours
        rng.integers(2, 10, n).astype(float),                # n_transits
        clip(rng.exponential(0.002, n), 0.0, 0.02),         # odd_even_diff: very low
        clip(rng.exponential(0.001, n), 0.0, 0.01),         # secondary_eclipse_strength: none
        clip(rng.normal(0.75, 0.1, n), 0.5, 1.0),           # transit_shape_score: U-shaped
        clip(rng.normal(0.85, 0.08, n), 0.5, 1.0),          # transit_symmetry: symmetric
        clip(rng.exponential(0.001, n), 0.0, 0.01),         # depth_uncertainty
        clip(rng.normal(0.85, 0.1, n), 0.0, 1.0),           # astronet_score: high
    ])
    X_parts.append(X0)
    y_parts.append(np.zeros(n, dtype=int))

    # Class 1: Eclipsing Binary
    X1 = np.column_stack([
        clip(rng.normal(0.08, 0.04, n), 0.01, 0.5),         # transit_depth: large
        clip(rng.normal(20.0, 8.0, n), 5.0, 80.0),          # snr: high
        clip(rng.normal(3.0, 2.0, n), 0.5, 15.0),           # orbital_period: short
        clip(rng.normal(3.5, 1.5, n), 0.5, 12.0),           # transit_duration_hours
        rng.integers(2, 15, n).astype(float),                # n_transits
        clip(rng.normal(0.03, 0.02, n), 0.005, 0.2),        # odd_even_diff: HIGH
        clip(rng.normal(0.04, 0.02, n), 0.005, 0.2),        # secondary_eclipse_strength: PRESENT
        clip(rng.normal(0.25, 0.1, n), 0.0, 0.5),           # transit_shape_score: V-shaped
        clip(rng.normal(0.80, 0.1, n), 0.4, 1.0),           # transit_symmetry
        clip(rng.exponential(0.003, n), 0.0, 0.02),         # depth_uncertainty
        clip(rng.normal(0.15, 0.1, n), 0.0, 0.5),           # astronet_score: low
    ])
    X_parts.append(X1)
    y_parts.append(np.ones(n, dtype=int))

    # Class 2: Blend / Contaminated Source
    X2 = np.column_stack([
        clip(rng.normal(0.003, 0.002, n), 0.0001, 0.015),   # transit_depth: shallow
        clip(rng.normal(5.0, 2.0, n), 1.0, 12.0),           # snr: low-moderate
        clip(rng.normal(8.0, 4.0, n), 0.5, 30.0),           # orbital_period
        clip(rng.normal(3.0, 1.5, n), 0.5, 10.0),           # transit_duration_hours
        rng.integers(1, 5, n).astype(float),                 # n_transits: few
        clip(rng.normal(0.01, 0.005, n), 0.0, 0.05),        # odd_even_diff: small
        clip(rng.normal(0.015, 0.01, n), 0.0, 0.06),        # secondary_eclipse_strength: weak
        clip(rng.normal(0.5, 0.15, n), 0.1, 0.9),           # transit_shape_score: mixed
        clip(rng.normal(0.55, 0.15, n), 0.2, 0.9),          # transit_symmetry: moderate
        clip(rng.exponential(0.003, n), 0.0, 0.02),         # depth_uncertainty
        clip(rng.normal(0.3, 0.15, n), 0.0, 0.7),           # astronet_score: intermediate
    ])
    X_parts.append(X2)
    y_parts.append(np.full(n, 2, dtype=int))

    # Class 3: Variable Star
    X3 = np.column_stack([
        clip(rng.normal(0.001, 0.001, n), 0.0, 0.008),      # transit_depth: very shallow
        clip(rng.normal(3.0, 1.5, n), 0.5, 7.0),            # snr: low
        clip(rng.normal(0.8, 0.4, n), 0.2, 3.0),            # orbital_period: short pulsation
        clip(rng.normal(4.0, 2.0, n), 0.5, 15.0),           # transit_duration_hours: long
        rng.integers(5, 20, n).astype(float),                # n_transits: many (pulsation)
        clip(rng.exponential(0.002, n), 0.0, 0.01),         # odd_even_diff
        clip(rng.exponential(0.001, n), 0.0, 0.005),        # secondary_eclipse_strength: none
        clip(rng.normal(0.4, 0.2, n), 0.0, 0.8),            # transit_shape_score: variable
        clip(rng.normal(0.6, 0.2, n), 0.1, 1.0),            # transit_symmetry
        clip(rng.exponential(0.005, n), 0.0, 0.03),         # depth_uncertainty: higher
        clip(rng.normal(0.1, 0.08, n), 0.0, 0.4),           # astronet_score: low
    ])
    X_parts.append(X3)
    y_parts.append(np.full(n, 3, dtype=int))

    # Class 4: False Positive / Noise
    X4 = np.column_stack([
        clip(rng.exponential(0.0005, n), 0.0, 0.003),       # transit_depth: near-zero
        clip(rng.uniform(0.0, 4.0, n), 0.0, 4.0),           # snr: below threshold
        clip(rng.uniform(0.5, 30.0, n), 0.5, 30.0),         # orbital_period: random
        clip(rng.uniform(0.5, 8.0, n), 0.5, 8.0),           # transit_duration_hours
        rng.integers(0, 3, n).astype(float),                 # n_transits: very few
        clip(rng.exponential(0.001, n), 0.0, 0.01),         # odd_even_diff
        clip(rng.exponential(0.001, n), 0.0, 0.01),         # secondary_eclipse_strength
        clip(rng.uniform(0.0, 1.0, n), 0.0, 1.0),           # transit_shape_score: random
        clip(rng.uniform(0.0, 1.0, n), 0.0, 1.0),           # transit_symmetry: random
        clip(rng.exponential(0.008, n), 0.0, 0.05),         # depth_uncertainty: large
        clip(rng.uniform(0.0, 0.3, n), 0.0, 0.3),           # astronet_score: very low
    ])
    X_parts.append(X4)
    y_parts.append(np.full(n, 4, dtype=int))

    X = np.vstack(X_parts)
    y = np.concatenate(y_parts)
    return X, y


def _get_model() -> RandomForestClassifier:
    """
    Return the singleton trained RandomForest classifier.
    Trains on first call using astrophysical priors.
    """
    global _model
    if _model is None:
        print('⚙️  Initialising rule-assisted heuristic classifier using astrophysical priors...')
        X, y = _generate_training_data(n_samples_per_class=600)
        _model = RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=3,
            class_weight='balanced',
            random_state=42,
            n_jobs=1,
        )
        _model.fit(X, y)
        print('✅ Classifier ready (5 classes, 200 decision trees).')
    return _model


def classify(
        features: dict,
        astronet_score: float = 0.0
) -> dict:
    """
    Classify a detected transit signal into one of five astrophysical signal types.

    The AstroNet CNN score is incorporated as a feature alongside BLS-derived
    astrophysical features, so that AstroNet contributes to the final vetting
    outcome rather than operating independently after classification.

    Args:
        features: Dictionary of extracted features from feature_extractor.extract_features().
        astronet_score: Raw AstroNet CNN prediction score in [0, 1]. Pass 0 if
                        unavailable or if this is a TESS target with domain shift.

    Returns:
        Dictionary containing:
            predicted_class: Human-readable label string.
            class_probabilities: Dict of {class_label: probability}.
            signal_color: 'green', 'yellow', or 'red' for UI rendering.
            feature_importance: Dict of {feature_name: importance_score (0-100)}.
    """
    model = _get_model()

    # Build feature vector in correct column order
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

    probs = model.predict_proba(feature_vector)[0]
    predicted_idx = int(np.argmax(probs))
    predicted_class = SIGNAL_CLASSES[predicted_idx]

    # Map to UI badge colour
    if predicted_idx == 0:       # Exoplanet Transit
        signal_color = 'green'
    elif predicted_idx in (1, 2, 3):  # Binary / Blend / Variable
        signal_color = 'yellow'
    else:                        # False Positive / Noise
        signal_color = 'red'

    # Feature importance (percentage contribution)
    importances = model.feature_importances_
    total = np.sum(importances)
    importance_dict = {
        name: round(float(imp / total) * 100, 1) if total > 0 else 0.0
        for name, imp in zip(FEATURE_NAMES, importances)
    }
    # Sort by magnitude descending
    importance_dict = dict(
        sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
    )

    class_probabilities = {
        SIGNAL_CLASSES[i]: round(float(p) * 100, 2)
        for i, p in enumerate(probs)
    }

    result = {
        'predicted_class':     predicted_class,
        'class_probabilities': class_probabilities,
        'signal_color':        signal_color,
        'feature_importance':  importance_dict,
    }

    print(f'✅ Classification result: {predicted_class}')
    print(f'   Probabilities:')
    for cls, prob in class_probabilities.items():
        print(f'     {cls}: {prob:.1f}%')

    return result


if __name__ == '__main__':
    # Standalone unit test
    test_features = {
        'transit_depth': 0.01,
        'snr': 14.5,
        'orbital_period': 5.07,
        'transit_duration_hours': 2.4,
        'n_transits': 4,
        'odd_even_diff': 0.001,
        'secondary_eclipse_strength': 0.0005,
        'transit_shape_score': 0.78,
        'transit_symmetry': 0.88,
        'depth_uncertainty': 0.0008,
    }
    result = classify(test_features, astronet_score=0.981)
    print('\nFeature importances:')
    for k, v in result['feature_importance'].items():
        print(f'  {k}: {v}%')
    print('\nStandalone test passed.')
