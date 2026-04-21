import sys
import time
import csv
import json
import os
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


# --- 2. CORE PATTERN ENGINE ---
@lru_cache(maxsize=None)
def get_feedback(secret, guess):
    if secret == guess: return "ggggg"
    res, s_list, g_list = ['_'] * 5, list(secret), list(guess)
    for i in range(5):
        if g_list[i] == s_list[i]:
            res[i] = 'g'
            s_list[i] = g_list[i] = None
    for i in range(5):
        if g_list[i] is not None:
            char = g_list[i]
            for j in range(5):
                if s_list[j] == char:
                    res[i] = 'y'
                    s_list[j] = None
                    break
    return "".join(res)


# --- 3. EASY MODE SEARCH ENGINE ---
@lru_cache(maxsize=200000)
def get_best_sim_move(pool_tuple, is_hard):
    pool = list(pool_tuple)
    if len(pool) <= 2: return pool[0]

    # In Easy Mode, we evaluate the ENTIRE dictionary for every move
    candidates = full_dictionary

    best_word, best_score = None, -1
    for cand in candidates:
        pg = {}
        for secret in pool:
            p = get_feedback(secret, cand)
            pg[p] = pg.get(p, 0) + 1

        # Scoring: Entropy + Pool Bonus
        score = len(pg) - (sum(v * v for v in pg.values()) / 100000)
        if cand in pool: score += 0.1

        if score > best_score:
            best_score, best_word = score, cand
    return best_word


def calculate_solve_analytics(candidate, is_hard, current_pool, current_turn):
    total_turns, max_turns, missed = 0, 0, []
    stats = [0] * 7
    pool_size = len(current_pool)

    for secret in current_pool:
        s_p, s_g, s_t = list(current_pool), candidate, current_turn
        while s_t <= 6:
            p = get_feedback(secret, s_g)
            if p == "ggggg":
                total_turns += s_t
                max_turns = max(max_turns, s_t)
                stats[s_t - 1] += 1
                break

            s_p = [w for w in s_p if get_feedback(w, s_g) == p]
            if not s_p: break

            if len(s_p) == 1:
                res_t = s_t + 1
                total_turns += res_t
                max_turns = max(max_turns, res_t)
                if res_t > 6:
                    missed.append(secret)
                    stats[6] += 1
                else:
                    stats[res_t - 1] += 1
                break

            s_t += 1
            if s_t > 6:
                missed.append(secret)
                total_turns += 7
                max_turns = 7
                stats[6] += 1
                break

            # Use Easy Mode Logic (is_hard=False)
            s_g = get_best_sim_move(tuple(s_p), False)

    win_p = ((pool_size - len(missed)) / pool_size) * 100
    exp = total_turns / pool_size
    return win_p, exp, max_turns, missed, stats


# --- 4. BATCH PLAYTHROUGH (EASY MODE) ---
def run_benchmark():
    load_data()
    LIMIT = 500
    starter = input("Enter starting word: ").lower().strip()

    # Force Easy Mode logic
    hard_mode = False

    save_dir = "/Users/marco/PyCharmMiscProject/"
    clean_tree_file = f"{save_dir}reast_clean.txt"

    global_stats, clean_tree_lines = [0] * 7, []
    decision_cache = {}
    start_time = time.time()

    print(f"\nStarting fresh 2315 Playthrough for '{starter.upper()}' (Easy Mode)...")

    for i in range(len(proper_word)):
        secret = proper_word[i]
        curr_word, curr_pool, turn, path, guess_list = starter, tuple(proper_word), 1, [], [starter]

        while turn <= 6:
            p = get_feedback(secret, curr_word)
            path.append(f"{curr_word}({p})")

            if p == "ggggg":
                global_stats[turn - 1] += 1
                break

            curr_pool = tuple([w for w in curr_pool if get_feedback(w, curr_word) == p])

            if len(curr_pool) == 1:
                turn += 1
                final_w = curr_pool[0]
                guess_list.append(final_w)
                if turn <= 6:
                    global_stats[turn - 1] += 1
                else:
                    global_stats[6] += 1
                path.append(f"{final_w}(ggggg)")
                break

            turn += 1
            if turn > 6:
                global_stats[6] += 1
                break

            state_key = curr_pool  # In Easy Mode, state is just the pool
            if state_key in decision_cache:
                curr_word = decision_cache[state_key]
            else:
                # In Easy Mode, candidates = EVERYTHING
                cands = full_dictionary
                base_recs = []
                for c in cands:
                    pg = {}
                    for s in curr_pool:
                        pat = get_feedback(s, c)
                        pg[pat] = pg.get(pat, 0) + 1
                    score = len(pg) - (sum(v * v for v in pg.values()) / 100000)
                    if c in curr_pool: score += 0.1
                    base_recs.append((c, score))

                base_recs.sort(key=lambda x: x[1], reverse=True)

                enriched = []
                for w_cand, _ in base_recs[:LIMIT]:
                    wp, exp, worst, miss, st = calculate_solve_analytics(w_cand, False, list(curr_pool), turn)
                    enriched.append((w_cand, wp, exp, worst, miss, st))

                # Sort: Win% -> Exp -> Worst
                enriched.sort(key=lambda x: (-x[1], x[2], x[3]))
                curr_word = enriched[0][0]
                decision_cache[state_key] = curr_word

            guess_list.append(curr_word)

        clean_tree_lines.append(",".join(guess_list))
        print(f"[{i + 1:04}] {secret.upper():<6} | {' -> '.join(path)}")

        if (i + 1) % 50 == 0:
            avg = (sum((j + 1) * global_stats[j] for j in range(6)) + (global_stats[6] * 7)) / (i + 1)
            print(f"\n--- Progress: {i + 1}/2315 | Avg: {avg:.4f} | {global_stats} ---\n")

    total_g = sum((j + 1) * global_stats[j] for j in range(6)) + (global_stats[6] * 7)
    summary = (
        f"Progress: 2315/2315\n"
        f"1: {global_stats[0]}\n2: {global_stats[1]}\n3: {global_stats[2]}\n"
        f"4: {global_stats[3]}\n5: {global_stats[4]}\n6: {global_stats[5]}\n"
        f"X: {global_stats[6]}\n\n"
        f"Average: {total_g / 2315:.3f}\n"
        f"Total # of guesses: {total_g}"
    )

    print("\n" + "=" * 30 + "\n" + summary + "\n" + "=" * 30)
    with open(clean_tree_file, "w") as f:
        f.write("\n".join(clean_tree_lines))
    with open(f"{save_dir}summary_{starter}.txt", "w") as f:
        f.write(summary)


if __name__ == "__main__":
    run_benchmark()
