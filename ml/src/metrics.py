"""Metrics with explicit support and undefined recall for absent labels."""
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def multilabel_metrics(truth, predicted, labels):
    truth, predicted = np.asarray(truth), np.asarray(predicted)
    p, r, f, support = precision_recall_fscore_support(truth, predicted, average=None, zero_division=0)
    micro = precision_recall_fscore_support(truth, predicted, average='micro', zero_division=0)
    return {
        'examples': len(truth), 'micro_precision': float(micro[0]), 'micro_recall': float(micro[1]),
        'micro_f1': float(micro[2]), 'macro_f1_all_labels_zero_undefined': float(np.mean(f)),
        'macro_f1_supported_labels': float(np.mean(f[support > 0])) if any(support > 0) else None,
        'exact_set_match': float(accuracy_score(truth, predicted)),
        'per_label': {label: {'precision': float(p[i]) if predicted[:, i].sum() else None,
                             'recall': float(r[i]) if support[i] else None,
                             'f1': float(f[i]) if support[i] or predicted[:, i].sum() else None,
                             'support': int(support[i]), 'predicted_positive': int(predicted[:, i].sum()),
                             'false_positives': int(((truth[:, i] == 0) & (predicted[:, i] == 1)).sum()),
                             'false_negatives': int(((truth[:, i] == 1) & (predicted[:, i] == 0)).sum())}
                      for i, label in enumerate(labels)}}


def encode(rows, labels, key='symptoms'):
    return np.array([[int(label in row[key]) for label in labels] for row in rows])
