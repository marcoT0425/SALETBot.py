import sys
import time
from functools import lru_cache

# --- 1. DATA LOADING ---
proper_word, word_list, full_dictionary = [], [], []


def load_data():
    global proper_word, word_list, full_dictionary
    try:
        with open("proper word.txt", "r", encoding="utf-8") as f:
            proper_word = [line.strip().lower() for line in f if len(line.strip()) == 5]
        with open("word list.txt", "r", encoding="utf-8") as f:
            word_list = [line.strip().lower() for line in f if len(line.strip()) == 5]
        full_dictionary = list(set(proper_word + word_list))
    except FileNotFoundError:
        sys.exit("CRITICAL ERROR: Dictionary files missing.")


# --- 2. FAST PATTERN ENGINE ---
@lru_cache(maxsize=None)
def get_feedback(secret, guess):
    if secret == guess: return "ggggg"
    res, s_list, g_list = ['_'] * 5, list(secret), list(guess)
    for i in range(5):
        if g_list[i] == s_list[i]:
            res[i], s_list[i], g_list[i] = 'g', None, None
    for i in range(5):
        if g_list[i] is not None:
            for j in range(5):
                if s_list[j] == g_list[i]:
                    res[i], s_list[j] = 'y', None
                    break
    return "".join(res)


# --- 3. DEEP HIERARCHICAL ANALYSIS ---
def get_metrics(cand, pool, current_turn):
    """Excel-style Hierarchy: Rate > Avg > Worst > 5+ Count"""
    total_guesses = 0
    worst = 0
    five_plus = 0
    solved = 0

    for secret in pool:
        # Mini-recursive solve for each secret in the sub-pool
        # To keep benchmark speed viable, we use a cached best-move for turn 3+
        turns = simulate_solve(secret, cand, pool, current_turn)
        if turns <= 6:
            solved += 1
            total_guesses += turns
            worst = max(worst, turns)
            if turns >= 5: five_plus += 1
        else:
            total_guesses += 7
            worst = 7
            five_plus += 1

    return (solved / len(pool), total_guesses / len(pool), worst, five_plus)


@lru_cache(maxsize=None)
def simulate_solve(secret, first_guess, initial_pool_tuple, start_turn):
    curr_pool = initial_pool_tuple
    curr_guess = first_guess
    for turn in range(start_turn, 7):
        pattern = get_feedback(secret, curr_guess)
        if pattern == "ggggg": return turn

        curr_pool = tuple(w for w in curr_pool if get_feedback(w, curr_guess) == pattern)
        if len(curr_pool) == 1: return turn + 1

        # Pick next move based on entropy (faster for deep sim)
        curr_guess = get_fast_move(curr_pool)
    return 7


@lru_cache(maxsize=None)
def get_fast_move(pool_tuple):
    # Entropy-only fallback for deep simulation speed
    best_ent, best_w = -1, pool_tuple[0]
    for cand in full_dictionary:
        counts = {}
        for s in pool_tuple:
            p = get_feedback(s, cand)
            counts[p] = counts.get(p, 0) + 1
        ent = len(counts) - (sum(v * v for v in counts.values()) / 100000)
        if cand in pool_tuple: ent += 0.1
        if ent > best_ent:
            best_ent, best_w = ent, cand
    return best_w


@lru_cache(maxsize=None)
def get_best_theoretical_move(pool_tuple, turn):
    # 1. Get Top 50 Entropy Candidates
    scored = []
    for cand in full_dictionary:
        counts = {}
        for s in pool_tuple:
            p = get_feedback(s, cand)
            counts[p] = counts.get(p, 0) + 1
        ent = len(counts) - (sum(v * v for v in counts.values()) / 100000)
        if cand in pool_tuple: ent += 0.1
        scored.append((cand, ent))
    scored.sort(key=lambda x: x[1], reverse=True)

    # 2. Strict Hierarchy Sort: Rate (Desc) -> Avg (Asc) -> Worst (Asc) -> 5+ (Asc)
    final_candidates = []
    for cand, _ in scored[:50]:
        metrics = get_metrics(cand, pool_tuple, turn)
        final_candidates.append((cand, metrics))

    # metrics = (rate, avg, worst, five_plus)
    # Sort order: -rate (desc), avg (asc), worst (asc), five_plus (asc)
    final_candidates.sort(key=lambda x: (-x[1][0], x[1][1], x[1][2], x[1][3]))
    return final_candidates[0][0]


# --- 4. CUMULATIVE BENCHMARK ---
def run_benchmark():
    load_data()
    starter = input("Enter Starter (e.g. CRATE): ").lower().strip()
    global_stats = [0] * 7

    for i, secret in enumerate(proper_word):
        curr_pool = tuple(proper_word)
        curr_guess = starter
        path = []

        for turn in range(1, 7):
            p = get_feedback(secret, curr_guess)
            path.append(f"{curr_guess}({p})")
            if p == "ggggg":
                global_stats[turn - 1] += 1
                break

            curr_pool = tuple(w for w in curr_pool if get_feedback(w, curr_guess) == p)
            if len(curr_pool) == 1:
                t = turn + 1
                if t <= 6:
                    global_stats[t - 1] += 1
                else:
                    global_stats[6] += 1
                path.append(f"{curr_pool[0]}(ggggg)")
                break

            if turn == 6:
                global_stats[6] += 1
                break

            curr_guess = get_best_theoretical_move(curr_pool, turn + 1)

        print(f"[{i + 1:04}] {secret.upper():<6} | {' -> '.join(path)}")


if __name__ == "__main__":
    run_benchmark()
