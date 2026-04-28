import sys
import time
import os
from functools import lru_cache
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- 1. DATA LOADING & FONTS ---
proper_word, word_list, full_dictionary = [], [], []


def load_data_and_fonts():
    global proper_word, word_list, full_dictionary
    try:
        with open("proper word.txt", "r", encoding="utf-8") as f:
            proper_word = [line.strip().lower() for line in f if len(line.strip()) == 5]
        with open("word list.txt", "r", encoding="utf-8") as f:
            word_list = [line.strip().lower() for line in f if len(line.strip()) == 5]
        full_dictionary = list(set(proper_word + word_list))

        fonts = {"Arial": ["arial.ttf", "Arial.ttf"], "CourierNew": ["cour.ttf", "Courier New.ttf"]}
        registered = {}
        for name, files in fonts.items():
            for f in files:
                if os.path.exists(f):
                    pdfmetrics.registerFont(TTFont(name, f))
                    registered[name] = name
                    break
        return registered.get("Arial", "Helvetica"), registered.get("CourierNew", "Courier")
    except FileNotFoundError:
        sys.exit("CRITICAL ERROR: Dictionary files missing.")


# --- 2. CORE ENGINES ---
@lru_cache(maxsize=None)
def get_feedback(secret, guess):
    if secret == guess: return "ggggg"
    res, s_list, g_list = ['_'] * 5, list(secret), list(guess)
    for i in range(5):
        if g_list[i] == s_list[i]:
            res[i] = 'g';
            s_list[i] = g_list[i] = None
    for i in range(5):
        if g_list[i] is not None:
            for j in range(5):
                if s_list[j] == g_list[i]:
                    res[i] = 'y';
                    s_list[j] = None;
                    break
    return "".join(res)


@lru_cache(maxsize=None)
def is_hard_mode_valid(guess, prev_guess, pattern):
    if not prev_guess or not pattern: return True
    for i, p in enumerate(pattern):
        if p == "g" and guess[i] != prev_guess[i]: return False
    req = {}
    for i, p in enumerate(pattern):
        if p in ("g", "y"):
            char = prev_guess[i];
            req[char] = req.get(char, 0) + 1
    for char, count in req.items():
        if guess.count(char) < count: return False
    return True


@lru_cache(maxsize=None)
def get_best_sim_move(pool_tuple, is_hard, prev_guess, last_pattern):
    pool = list(pool_tuple)
    if len(pool) <= 2: return pool[0]
    candidates = full_dictionary if not is_hard else [c for c in full_dictionary if
                                                      is_hard_mode_valid(c, prev_guess, last_pattern)]
    best_word, best_score = None, -1
    for cand in candidates:
        pg = {}
        for secret in pool:
            p = get_feedback(secret, cand);
            pg[p] = pg.get(p, 0) + 1
        score = len(pg) - (sum(c * c for c in pg.values()) / 100000)
        if cand in pool: score += 0.1
        if score > best_score: best_score, best_word = score, cand
    return best_word


@lru_cache(maxsize=None)
def calculate_solve_analytics(candidate, is_hard, current_pool, current_turn):
    total_turns, stats, pool_size = 0, [0] * 7, len(current_pool)
    if pool_size == 0: return 0, 0, 7, 0, False
    for secret in current_pool:
        s_p, s_g, s_t = list(current_pool), candidate, current_turn
        while s_t <= 6:
            p = get_feedback(secret, s_g)
            if p == "ggggg":
                total_turns += s_t;
                stats[s_t - 1] += 1
                break
            s_p = tuple([w for w in s_p if get_feedback(w, s_g) == p])
            if not s_p: break
            if len(s_p) == 1:
                res_t = s_t + 1;
                total_turns += res_t if res_t <= 6 else 7
                stats[min(res_t - 1, 6)] += 1;
                break
            s_t += 1
            if s_t > 6: stats[6] += 1; total_turns += 7; break
            s_g = get_best_sim_move(s_p, is_hard, s_g, p)
    win_p = ((pool_size - stats[6]) / pool_size) * 100
    exp = total_turns / pool_size
    worst = 7 if stats[6] > 0 else max([i + 1 for i, v in enumerate(stats) if v > 0])
    four_plus = sum(stats[3:])
    return win_p, exp, worst, four_plus, (candidate in current_pool)


# --- 3. PERFECT PDF TREE LOGIC ---
def generate_tree_pdf(start_word, results_dict, font_main, font_mono):
    # Sort by pattern path to ensure vertical alignment of shared branches
    sorted_targets = sorted(results_dict.keys(), key=lambda t: [p for w, p in results_dict[t]])
    c = canvas.Canvas(f"{start_word}_tree.pdf", pagesize=A4)
    w, h = A4
    y, box, margin = h - 80, 10, 1.5
    word_w, col_w = (box + margin) * 5, (box + margin) * 5 + 35
    colors_map = {'g': colors.HexColor("#6aaa64"), 'y': colors.HexColor("#c9b458"), '_': colors.HexColor("#787c7e")}
    c.setFont(font_main, 16);
    c.drawString(40, h - 40, f"WORDLE DECISION TREE: {start_word.upper()}")
    prev_h = None
    for target in sorted_targets:
        if y < 50: c.showPage(); y = h - 60; prev_h = None
        history, x = results_dict[target], 40
        for i, (word, pattern) in enumerate(history):
            is_rep = prev_h and i < len(prev_h) and prev_h[i] == (word, pattern)
            if is_rep:
                c.setFillColor(colors.black);
                c.setFont("Helvetica-Bold", 10);
                c.drawCentredString(x + word_w / 2, y + 2, "↓")
            else:
                for ci, pc in enumerate(pattern):
                    bx = x + (ci * (box + margin))
                    c.setFillColor(colors_map.get(pc, colors.gray));
                    c.rect(bx, y, box, box, stroke=0, fill=1)
                    c.setFillColor(colors.white);
                    c.setFont(font_mono, 7);
                    c.drawCentredString(bx + box / 2, y + 2.5, word[ci].upper())
            if i < len(history) - 1:
                arrow = "↓" if prev_h and i + 1 < len(prev_h) and history[i] == prev_h[i] and history[i + 1] == prev_h[
                    i + 1] else "→"
                if is_rep and not (prev_h and i + 1 < len(prev_h) and prev_h[i + 1] == history[i + 1]): arrow = "→"
                c.setFillColor(colors.black);
                c.setFont("Helvetica-Bold", 10);
                c.drawCentredString(x + word_w + 15, y + 2, arrow)
            x += col_w
        prev_h = history;
        y -= 18
    c.save()


# --- 4. CUMULATIVE TESTER ---
def run_cumulative_test():
    f_main, f_mono = load_data_and_fonts();
    start_word = input("Start Word: ").lower().strip()
    hard_mode = input("Hard mode? (Y/N): ").lower() == "y";
    LIMIT = 140
    global_stats, results_dict, best_move_memo = [0] * 7, {}, {}
    total_turns, start_time = 0, time.time()

    for idx, target in enumerate(proper_word, 1):
        pool, history, turn = tuple(proper_word), [], 1
        game_log = []
        # UI Progress
        sys.stdout.write(
            f"\rProgress: {idx}/{len(proper_word)} | Target: {target.upper()} | Avg: {total_turns / max(1, idx - 1):.4f}")
        sys.stdout.flush()

        while turn <= 6:
            guess = start_word if turn == 1 else best_move_memo[state_key]
            pattern = get_feedback(target, guess)
            game_log.append((guess, pattern))
            if pattern == "ggggg": break
            pool = tuple([w for w in pool if get_feedback(w, guess) == pattern])
            turn += 1
            if turn > 6: break
            state_key = (pool, turn, hard_mode)
            if state_key not in best_move_memo:
                recs = []
                cands = full_dictionary if not hard_mode else [c for c in full_dictionary if
                                                               is_hard_mode_valid(c, guess, pattern)]
                for c in cands:
                    pg = {}
                    for s in pool: p = get_feedback(s, c); pg[p] = pg.get(p, 0) + 1
                    score = len(pg) - (sum(v * v for v in pg.values()) / 100000)
                    if c in pool: score += 0.1
                    recs.append((c, score))
                recs.sort(key=lambda x: x[1], reverse=True)
                enriched = []
                for w, _ in recs[:LIMIT]:
                    wp, exp, worst, fpc, ic = calculate_solve_analytics(w, hard_mode, pool, turn)
                    enriched.append((w, wp, exp, worst, fpc, ic))
                enriched.sort(key=lambda x: (-x[1], x[2], x[3], x[4], x[0]))
                best_move_memo[state_key] = enriched[0][0]

        results_dict[target] = game_log
        global_stats[min(turn - 1, 6)] += 1;
        total_turns += (turn if turn <= 6 else 7)

    generate_tree_pdf(start_word, results_dict, f_main, f_mono)
    print(f"\nDone! PDF saved as {start_word}_tree.pdf")


if __name__ == "__main__":
    run_cumulative_test()
