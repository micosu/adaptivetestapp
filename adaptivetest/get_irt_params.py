import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math


df = pd.read_csv('only_lexile_all_columns.csv')

log_gen_freqs = np.log(df['gen_freq'] + 1)
min_log_freq = log_gen_freqs.min()
max_log_freq = log_gen_freqs.max()

def compute_irt_params_(word_attrs):
    # Difficulty
    age_centered = word_attrs['age_of_acq'] - 8
    lexile_centered = (word_attrs['lexile'] - 700) / 100
    grade_centered = word_attrs['word_grade'] - 3
    b = 0.4 * age_centered + 0.4 * lexile_centered + 0.2 * grade_centered

    # Discrimination
    syllables = word_attrs['syllables']
    fiction_rank = word_attrs['fiction_rank']
    a = 1.0 + 0.5 * ((3 - syllables) / 2 + (math.log10(fiction_rank + 1) - 3))
    a = max(0.5, min(a, 2.5))

    # Guessing
    gen_freq = word_attrs['gen_freq']
    norm_freq = (math.log(gen_freq + 1) - min_log_freq) / (max_log_freq - min_log_freq)
    c = 0.2 + 0.15 * norm_freq
    c = max(0.2, min(c, 0.35))

    return a, b, c

def compute_irt_params(row, min_log_freq, max_log_freq):
    age_centered = row['age_of_acq'] - 8
    lexile_centered = (row['lexile'] - 700) / 100
    try:
        grade_centered = int(row['word_grade'][0]) - 3
    except TypeError:
        grade_centered = 10
    b = 0.4 * age_centered + 0.4 * lexile_centered + 0.2 * grade_centered
    b = np.clip(b, -3, 3)

    a = 1.0 + 0.5 * ((3 - row['syllables']) / 2 + (math.log10(row['fiction_rank'] + 1) - 3))
    a = max(0.5, min(a, 2.5))

    norm_freq = (math.log(row['gen_freq'] + 1) - min_log_freq) / (max_log_freq - min_log_freq)
    c = 0.2 + 0.15 * norm_freq
    c = max(0.2, min(c, 0.35))

    return pd.Series({'a': a, 'b': b, 'c': c})




df[['a', 'b', 'c']] = df.apply(compute_irt_params, axis=1, args=(min_log_freq, max_log_freq))

# === Plotting the distributions ===
fig, axs = plt.subplots(1, 3, figsize=(18, 5))

axs[0].hist(df['a'], bins=20, color='skyblue', edgecolor='black')
axs[0].set_title("Discrimination (a) Distribution")
axs[0].set_xlabel("a value")
axs[0].set_ylabel("Frequency")

axs[1].hist(df['b'], bins=20, color='salmon', edgecolor='black')
axs[1].set_title("Difficulty (b) Distribution")
axs[1].set_xlabel("b value")

axs[2].hist(df['c'], bins=20, color='lightgreen', edgecolor='black')
axs[2].set_title("Guessing (c) Distribution")
axs[2].set_xlabel("c value")

plt.tight_layout()
plt.show()