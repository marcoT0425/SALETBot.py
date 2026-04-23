import sys
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
        sys.exit("CRITICAL ERROR: Dictionary files missing (proper word.txt / word list.txt).")


# --- 2. CORE PATTERN & ANALYTICS ---
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


def is_hard_mode_valid(guess, prev_guess, pattern):
    if not prev_guess or not pattern: return True
    for i, p in enumerate(pattern):
        if p == "g" and guess[i] != prev_guess[i]: return False
    required_counts = {}
    for i, p in enumerate(pattern):
        if p in ("g", "y"):
            char = prev_guess[i]
            required_counts[char] = required_counts.get(char, 0) + 1
    for char, count in required_counts.items():
        if guess.count(char) < count: return False
    return True


@lru_cache(maxsize=None)
def get_best_sim_move(pool_tuple, is_hard, prev_guess, last_pattern):
    pool = list(pool_tuple)
    if len(pool) <= 2: return pool[0]
    best_word, best_score = None, -1
    candidates = full_dictionary if not is_hard else [c for c in full_dictionary if
                                                      is_hard_mode_valid(c, prev_guess, last_pattern)]
    for cand in candidates:
        pattern_groups = {}
        for secret in pool:
            p = get_feedback(secret, cand)
            pattern_groups[p] = pattern_groups.get(p, 0) + 1
        score = len(pattern_groups) - (sum(c * c for c in pattern_groups.values()) / 100000)
        if cand in pool: score += 0.1
        if score > best_score:
            best_score, best_word = score, cand
    return best_word


def calculate_solve_analytics(candidate, is_hard, current_pool, current_turn):
    total_turns, stats = 0, [0] * 7
    pool_size = len(current_pool)
    for secret in current_pool:
        s_p, s_g, s_t = list(current_pool), candidate, current_turn
        while s_t <= 6:
            p = get_feedback(secret, s_g)
            if p == "ggggg":
                total_turns += s_t
                stats[s_t - 1] += 1
                break
            s_p = [w for w in s_p if get_feedback(w, s_g) == p]
            if not s_p: break
            if len(s_p) == 1:
                res_t = s_t + 1
                total_turns += res_t if res_t <= 6 else 7
                stats[min(res_t - 1, 6)] += 1
                break
            s_t += 1
            if s_t > 6:
                stats[6] += 1;
                total_turns += 7;
                break
            s_g = get_best_sim_move(tuple(s_p), is_hard, s_g, p)
    win_p = ((pool_size - stats[6]) / pool_size) * 100
    exp = total_turns / pool_size
    worst = 7 if stats[6] > 0 else (6 if stats[5] > 0 else (5 if stats[4] > 0 else 4))
    four_plus = sum(stats[3:])
    return win_p, exp, worst, four_plus, (candidate in current_pool)


# --- 3. CUMULATIVE TESTER ENGINE ---
def run_cumulative_test():
    load_data()
    start_word = input("Enter starting word: ").lower().strip()
    hard_mode = input("Hard mode? (Y/N): ").lower() == "y"
    LIMIT = 130

    global_stats = [0] * 7
    playthrough_log = []
    clean_output = []  # Added for the requested .csv style output
    best_move_memo = {}

    print(f"\n--- Testing {len(proper_word)} words starting with '{start_word}' ---\n")

    for idx, target in enumerate(proper_word, 1):
        current_pool = tuple(proper_word)
        history = [start_word]
        turn = 1

        while turn <= 6:
            pattern = get_feedback(target, history[-1])
            if pattern == "ggggg": break

            current_pool = tuple([w for w in current_pool if get_feedback(w, history[-1]) == pattern])
            turn += 1
            if turn > 6: break

            if current_pool in best_move_memo:
                next_move = best_move_memo[current_pool]
            else:
                base_recs = []
                cands = full_dictionary if not hard_mode else [c for c in full_dictionary if
                                                               is_hard_mode_valid(c, history[-1], pattern)]

                for c in cands:
                    pg = {}
                    for s in current_pool:
                        p = get_feedback(s, c)
                        pg[p] = pg.get(p, 0) + 1
                    score = len(pg) - (sum(v * v for v in pg.values()) / 100000)
                    if c in current_pool: score += 0.1
                    base_recs.append((c, score))

                base_recs.sort(key=lambda x: x[1], reverse=True)
                enriched = []
                for w, _ in base_recs[:LIMIT]:
                    wp, exp, worst, fpc, ic = calculate_solve_analytics(w, hard_mode, current_pool, turn)
                    enriched.append((w, wp, exp, worst, fpc, ic))

                enriched.sort(key=lambda x: (-x[1], x[2], x[3], x[5], x[0]))
                next_move = enriched[0][0]
                best_move_memo[current_pool] = next_move

            history.append(next_move)

        res_idx = turn - 1 if turn <= 6 else 6
        global_stats[res_idx] += 1

        # ADDED: Store the comma-separated playthrough line
        clean_output.append(",".join(history))

        current_playthrough = f"{target.upper()}: {' -> '.join(history)} ({'X' if turn > 6 else turn})"
        playthrough_log.append(current_playthrough)
        print(f"[{idx}/{len(proper_word)}] {current_playthrough}")

    # --- 4. FILE EXPORT ---
    # FIXED: Now exports each path as "starter,guess2,target" on its own line
    with open(f"{start_word}_clean.txt", "w") as f:
        f.write("\n".join(clean_output))

    with open("stats.txt", "w") as f:
        f.write(f"Cumulative Test for: {start_word.upper()}\n")
        f.write(f"Distribution [1,2,3,4,5,6,X]: {global_stats}\n\n")
        f.write("FULL PLAYTHROUGH LOG:\n" + "\n".join(playthrough_log))

    print(f"\nFinished! Results saved to {start_word}_clean.txt and stats.txt")


if __name__ == "__main__":
    run_cumulative_test()
