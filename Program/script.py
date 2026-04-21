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


def get_block_row(pattern):
    mapping = {'g': '█', 'y': '▒', '_': '░'}
    return "".join(mapping.get(c, '░') for c in pattern)


# --- 3. THEORETICAL SEARCH ENGINE ---
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


@lru_cache(maxsize=200000)
def get_best_sim_move(pool_tuple, is_hard, prev_guess, last_pattern):
    """Finds the theoretical best move for a pool to minimize turns."""
    pool = list(pool_tuple)
    if len(pool) <= 2: return pool[0]

    candidates = full_dictionary
    if is_hard:
        candidates = [c for c in full_dictionary if is_hard_mode_valid(c, prev_guess, last_pattern)]

    best_word = None
    best_score = -1

    for cand in candidates:
        pattern_groups = {}
        for secret in pool:
            p = get_feedback(secret, cand)
            pattern_groups[p] = pattern_groups.get(p, 0) + 1

        # Entropy Score
        score = len(pattern_groups) - (sum(c * c for c in pattern_groups.values()) / 100000)
        if cand in pool: score += 0.1

        if score > best_score:
            best_score = score
            best_word = cand
    return best_word


def calculate_solve_analytics(candidate, is_hard, current_pool, current_turn):
    total_turns, max_turns, missed = 0, 0, []
    # stats indices: 0=1s, 1=2s, 2=3s, 3=4s, 4=5s, 5=6s, 6=X
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

            s_g = get_best_sim_move(tuple(s_p), is_hard, s_g, p)

    win_p = ((pool_size - len(missed)) / pool_size) * 100
    exp = total_turns / pool_size
    return win_p, exp, max_turns, missed, stats


# --- 4. MAIN INTERFACE ---
def run_solver():
    load_data()
    LIMIT = 100  # Higher for precision, lower for speed
    print(f"\nWordle Solver v15.0 (Theoretical Mode)")
    hard_mode = input("Hard mode? (Y/N): ").lower() == "y"

    guessing_word = "salet" if hard_mode else "crane"
    propers_remaining = proper_word.copy()
    turn_count, last_word_used, pattern_history = 0, "", []

    while True:
        turn_count += 1
        print(f"\nCandidates left: {len(propers_remaining)}")

        if turn_count > 1:
            # Initial broad filter
            base_recs = []
            cands = full_dictionary if not hard_mode else [c for c in full_dictionary if
                                                           is_hard_mode_valid(c, last_word_used,
                                                                              pattern_history[-1][1])]
            for c in cands:
                pg = {}
                for s in propers_remaining:
                    p = get_feedback(s, c)
                    pg[p] = pg.get(p, 0) + 1
                score = len(pg) - (sum(v * v for v in pg.values()) / 100000)
                if c in propers_remaining: score += 0.1
                base_recs.append((c, score))

            base_recs.sort(key=lambda x: x[1], reverse=True)
            actual_to_analyze = min(len(base_recs), LIMIT)
            print(f"Theoretical Analysis of Top {actual_to_analyze}...")

            enriched = []
            for i, (w, _) in enumerate(base_recs[:actual_to_analyze], 1):
                wp, exp, worst, miss, st = calculate_solve_analytics(w, hard_mode, propers_remaining, turn_count)
                enriched.append((w, wp, exp, worst, miss, st))
                sys.stdout.write(f"\rProgress: {int((i / actual_to_analyze) * 100)}%")
                sys.stdout.flush()

            print("\n\n" + f"{'WORD':<10} | {'WIN %':<7} | {'EXP':<7} | {'WORST'} | {'STATS [1,2,3,4,5,6,X]'}")
            print("-" * 95)

            # SORTING: Win% (Desc) -> Expectancy (Asc) -> Worst (Asc)
            enriched.sort(key=lambda x: (-x[1], x[2], x[3]))

            for rw, wp, rg, rwst, rm, rst in enriched[:15]:
                print(f"{rw.upper():<10} | {wp:<7.1f} | {rg:.3f} | {rwst:<5} | {rst}")
            guessing_word = enriched[0][0]

        raw_in = input(f"\nPattern for '{guessing_word}': ").lower().strip().split()
        if not raw_in: continue
        p = raw_in[1] if len(raw_in) > 1 else raw_in[0]
        w = raw_in[0] if len(raw_in) > 1 else guessing_word

        pattern_history.append((w, p))
        last_word_used = w
        if p == "ggggg": break
        propers_remaining = [word for word in propers_remaining if get_feedback(word, w) == p]


if __name__ == "__main__":
    run_solver()
