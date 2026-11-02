import os
import time
import random
import streamlit as st

st.set_page_config(page_title="스도쿠", page_icon="🧩")   # 항상 맨 처음에 실행

# ─────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RANKING_FILE = os.path.join(BASE_DIR, "ranking.txt")   # 랭킹 저장 파일 (PyQt 버전과 같은 형식)
TOP_N = 10
DIGITS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]   # 입력 가능한 숫자


# ─────────────────────────────────────────────
# [secret 기능] .streamlit/secrets.toml 값 읽기
# ─────────────────────────────────────────────
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:          # secrets.toml 파일이 없거나 key가 없을 때
        return default


GAME_TITLE = get_secret("game_title", "스도쿠")


# ─────────────────────────────────────────────
# [데코레이터 1] @st.cache_data
#  - rerun 될 때마다 다시 계산/파일읽기 하지 않고 캐시에서 꺼내 씀
# ─────────────────────────────────────────────
@st.cache_data()
def load_base_board():
    # PyQt 버전의 AVal(완성된 스도쿠 판) 역할
    # (i*3 + i//3 + j) % 9 + 1 공식은 행/열/3x3칸 규칙을 모두 만족하는 완성판을 만든다
    return [[str((i * 3 + i // 3 + j) % 9 + 1) for j in range(9)] for i in range(9)]


@st.cache_data()
def load_ranking():
    rankings = []
    try:
        with open(RANKING_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    continue
                try:
                    rankings.append((parts[0], float(parts[1])))
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    rankings.sort(key=lambda x: x[1])
    return rankings


def save_ranking(name, elapsed_seconds):
    with open(RANKING_FILE, "a", encoding="utf-8") as f:
        f.write("%s,%.4f\n" % (name, elapsed_seconds))
    load_ranking.clear()       # 파일이 바뀌었으니 캐시 비우기


def get_rank(rankings, name, elapsed_seconds):
    for idx, (n, t) in enumerate(rankings):
        if n == name and abs(t - elapsed_seconds) < 0.0001:
            return idx + 1
    return len(rankings)


def format_time(seconds):
    m = int(seconds // 60)
    s = seconds % 60
    return "%d분 %.2f초" % (m, s)


# ─────────────────────────────────────────────
# 정답 검사용 함수 (PyQt 버전 로직 그대로)
# ─────────────────────────────────────────────
def find_duplicate(cells):
    seen = {}
    for (r, c, v) in cells:
        if v == "":
            continue
        if v in seen:
            return seen[v], (r, c)
        seen[v] = (r, c)
    return None


def build_wrong_message(dup, user_cells):
    (r1, c1), (r2, c2) = dup
    wrong_cells = [pos for pos in [(r1, c1), (r2, c2)] if pos in user_cells]
    if not wrong_cells:
        wrong_cells = [(r1, c1), (r2, c2)]
    text = ", ".join("%d행 %d열" % (r + 1, c + 1) for (r, c) in wrong_cells)
    return text + " 오답."


def check_board(values, user_cells):
    """(성공여부, 메시지) 반환"""
    # 1) 빈칸 검사
    for i in range(9):
        for j in range(9):
            if values[i][j] == "":
                return False, "%d행 %d열이 비어있어요." % (i + 1, j + 1)
    # 2) 행 검사
    for i in range(9):
        dup = find_duplicate([(i, j, values[i][j]) for j in range(9)])
        if dup:
            return False, build_wrong_message(dup, user_cells)
    # 3) 열 검사
    for j in range(9):
        dup = find_duplicate([(i, j, values[i][j]) for i in range(9)])
        if dup:
            return False, build_wrong_message(dup, user_cells)
    # 4) 3x3 칸 검사
    for bi in [0, 3, 6]:
        for bj in [0, 3, 6]:
            cells = [(bi + di, bj + dj, values[bi + di][bj + dj])
                     for di in range(3) for dj in range(3)]
            dup = find_duplicate(cells)
            if dup:
                return False, build_wrong_message(dup, user_cells)
    return True, "!!! ~~~Congratulation~~~ !!!"


# ─────────────────────────────────────────────
# [전역변수] st.session_state
#  - rerun 되어도 값이 유지되는 변수들
# ─────────────────────────────────────────────
def cell_key(i, j):
    return "cell_%d_%d_%d" % (st.session_state.game_id, i, j)


def new_game():
    """PyQt 버전의 ShuffleClick"""
    # 이전 게임의 입력칸 값 지우기
    for key in list(st.session_state.keys()):
        if str(key).startswith("cell_") or str(key).startswith("given_"):
            del st.session_state[key]

    base = load_base_board()
    random19 = list(range(1, 10))
    random.shuffle(random19)
    p = st.session_state.get("ratio", 0.5)      # 숫자가 보일 확률 (PyQt의 pEdit)

    board = [[str(random19[int(base[i][j]) - 1]) for j in range(9)] for i in range(9)]
    user_cells = set()
    for i in range(9):
        for j in range(9):
            if random.random() > p:
                user_cells.add((i, j))          # 이 칸은 빈칸 → 사용자가 입력

    st.session_state.game_id = st.session_state.get("game_id", 0) + 1
    st.session_state.board = board
    st.session_state.user_cells = user_cells
    st.session_state.start_time = time.time()
    st.session_state.finished = False
    st.session_state.final_time = 0.0
    st.session_state.result = None          # (종류, 메시지)
    st.session_state.registered = False
    st.session_state.rank_msg = ""
    st.session_state.show_balloons = False


def check_answer():
    """PyQt 버전의 CompleteTestClick"""
    if st.session_state.finished:
        return
    board = st.session_state.board
    values = []
    for i in range(9):
        row = []
        for j in range(9):
            if (i, j) in st.session_state.user_cells:
                v = str(st.session_state.get(cell_key(i, j), "")).strip()
                if v != "" and v not in DIGITS:
                    st.session_state.result = ("error", "%d행 %d열에는 1~9 숫자만 입력할 수 있어요." % (i + 1, j + 1))
                    return
                row.append(v)
            else:
                row.append(board[i][j])
        values.append(row)

    ok, msg = check_board(values, st.session_state.user_cells)
    if ok:
        st.session_state.finished = True
        st.session_state.final_time = round(time.time() - st.session_state.start_time, 4)
        st.session_state.result = ("success", msg)
        st.session_state.show_balloons = True
    else:
        st.session_state.result = ("error", msg)


def register_ranking():
    """PyQt 버전의 finishGame (이름 입력 → 랭킹 저장)"""
    if not st.session_state.finished or st.session_state.registered:
        return
    name = st.session_state.get("player_name", "").strip().replace(",", " ")
    if name == "":
        name = "익명"
    elapsed = st.session_state.final_time
    save_ranking(name, elapsed)
    my_rank = get_rank(load_ranking(), name, elapsed)
    st.session_state.registered = True
    st.session_state.rank_msg = "%s님 완료 시간: %s / 현재 순위: %d위" % (name, format_time(elapsed), my_rank)


def reset_ranking():
    """PyQt 버전의 resetRanking (Ctrl+R) → secrets.toml 관리자 비밀번호로 보호"""
    admin_pw = get_secret("admin_password")
    typed = st.session_state.get("admin_pw", "")
    if admin_pw is None:
        st.session_state.reset_msg = ("warning", "secrets.toml에 admin_password가 없어요.")
    elif typed == str(admin_pw):
        open(RANKING_FILE, "w", encoding="utf-8").close()
        load_ranking.clear()
        st.session_state.reset_msg = ("success", "랭킹 기록이 모두 삭제되었습니다.")
    else:
        st.session_state.reset_msg = ("error", "비밀번호가 틀렸어요.")
    st.session_state.admin_pw = ""


# 처음 접속했을 때 한 번만 게임 생성
if "board" not in st.session_state:
    new_game()
if "reset_msg" not in st.session_state:
    st.session_state.reset_msg = None


# ─────────────────────────────────────────────
# [데코레이터 2] @st.fragment(run_every=1)
#  - 1초마다 이 함수만 다시 실행 → 전체 rerun 없이 타이머만 갱신 (PyQt의 QTimer 역할)
# ─────────────────────────────────────────────
@st.fragment(run_every=1)
def show_timer():
    if st.session_state.finished:
        elapsed = st.session_state.final_time
    else:
        elapsed = time.time() - st.session_state.start_time
    elapsed = int(elapsed)
    st.metric("⏱ 경과 시간", "%02d:%02d" % (elapsed // 60, elapsed % 60))


# ─────────────────────────────────────────────
# 화면 구성
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* 스도쿠 칸만 골라내기: 칸의 라벨이 "N행 M열"이라서 aria-label이 "열"로 끝나는 입력칸만 해당 */
input[aria-label$="열"] {
    text-align: center; font-weight: bold; font-size: 20px;
}
/* 사용자가 입력하는 칸: 빨간 글씨 (PyQt 버전처럼) */
input[aria-label$="열"]:not(:disabled) {
    color: red; -webkit-text-fill-color: red;
}
/* 주어진 숫자 칸: 흐리게 보이지 않도록 진한 글씨 + 회색 배경 */
input[aria-label$="열"]:disabled {
    color: #31333F; -webkit-text-fill-color: #31333F; opacity: 1; cursor: default;
}
div:has(> input[aria-label$="열"]:disabled) {
    background-color: #DCDCE2; opacity: 1;
}
/* form 안 입력칸의 "Press Enter to submit form" 안내 문구 숨기기 */
div[data-testid="InputInstructions"] { display: none; }
</style>
""", unsafe_allow_html=True)

st.title("🧩 " + GAME_TITLE)

# 사이드바: 게임 설정 + 랭킹 초기화
with st.sidebar:
    st.header("게임 설정")
    st.slider("숫자가 보일 확률", 0.2, 0.9, 0.5, 0.05, key="ratio")
    st.caption("새 게임을 눌러야 적용돼요.")
    st.button("🔀 새 게임 (Shuffle)", on_click=new_game)

    st.divider()
    st.header("랭킹 초기화")
    st.text_input("관리자 비밀번호", type="password", key="admin_pw")
    st.button("🗑 랭킹 초기화", on_click=reset_ranking)
    if st.session_state.reset_msg:
        kind, text = st.session_state.reset_msg
        if kind == "success":
            st.success(text)
        elif kind == "warning":
            st.warning(text)
        else:
            st.error(text)

show_timer()

# 스도쿠 판: form으로 감싸서 숫자를 입력할 때마다 rerun되지 않고
# "완료 확인"을 눌렀을 때만 한 번 실행되게 함 (속도 개선)
# 3x3 칸마다 테두리 상자(container)로 감싸서 구분선 표시
with st.form("board_form", border=False):
    board = st.session_state.board
    for bi in range(3):                          # 큰 칸 행 (0~2)
        box_cols = st.columns(3)
        for bj in range(3):                      # 큰 칸 열 (0~2)
            with box_cols[bj]:
                with st.container(border=True):  # ← 이 테두리가 3x3 구분선
                    for di in range(3):
                        cell_cols = st.columns(3)
                        for dj in range(3):
                            i = bi * 3 + di      # 실제 행 번호
                            j = bj * 3 + dj      # 실제 열 번호
                            with cell_cols[dj]:
                                # 모든 칸을 같은 text_input으로 만들어 높이/간격을 똑같이 맞춤
                                if (i, j) in st.session_state.user_cells:
                                    # 빈칸: 사용자가 입력 (빨간 글씨)
                                    st.text_input("%d행 %d열" % (i + 1, j + 1),
                                                  key=cell_key(i, j),
                                                  max_chars=1,
                                                  label_visibility="collapsed")
                                else:
                                    # 주어진 숫자: 수정 못 하게 disabled (검은 글씨)
                                    st.text_input("%d행 %d열" % (i + 1, j + 1),
                                                  value=board[i][j],
                                                  key="given_%d_%d_%d" % (st.session_state.game_id, i, j),
                                                  label_visibility="collapsed",
                                                  disabled=True)

    st.form_submit_button("✅ 완료 확인", on_click=check_answer, type="primary",
                          disabled=st.session_state.finished)

# 결과 메시지 (PyQt의 resEdit)
if st.session_state.result:
    kind, text = st.session_state.result
    if kind == "success":
        st.success(text + "  (기록: %s)" % format_time(st.session_state.final_time))
        if st.session_state.show_balloons:      # 풍선은 성공한 순간 한 번만
            st.balloons()
            st.session_state.show_balloons = False
    else:
        st.error(text)

# 완료 후 이름 입력 → 랭킹 등록 (PyQt의 QInputDialog)
if st.session_state.finished:
    if not st.session_state.registered:
        st.text_input("이름을 입력하세요 (비우면 '익명')", key="player_name")
        st.button("🏆 랭킹 등록", on_click=register_ranking)
    else:
        st.info(st.session_state.rank_msg)

# 랭킹 TOP 10
st.subheader("🏆 전체 랭킹 TOP %d" % TOP_N)
rankings = load_ranking()
if rankings:
    st.table([{"순위": "%d위" % (idx + 1), "이름": n, "기록": format_time(t)}
              for idx, (n, t) in enumerate(rankings[:TOP_N])])
else:
    st.write("(기록 없음)")
