import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List

# ===========================
# --------- CONFIG ----------
# ===========================
st.set_page_config(
    page_title="Exam Management System",
    page_icon="📚",
    layout="wide",
    menu_items={"about": "Exam Management • Streamlit"}
)

# ---------- Custom CSS (Beautiful Interface) ----------
CUSTOM_CSS = """
<style>
:root {
  --card-bg: #ffffff;
  --muted: #6b7280;
  --primary: #4f46e5;
  --accent: #10b981;
  --danger: #ef4444;
  --soft: #f8fafc;
  --soft-2: #f1f5f9;
}
.block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; }
h1, h2, h3 { letter-spacing: -0.02em; }
.card {
  background: var(--card-bg);
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 10px 22px rgba(0,0,0,0.04), 0 2px 6px rgba(0,0,0,0.04);
  border: 1px solid #e5e7eb;
}
.card.soft { background: var(--soft); border-color: #e2e8f0; }
.badge {
  display:inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px;
  background: #EEF2FF; color: #3730A3; border: 1px solid #E0E7FF; margin-left: 8px;
}
.kpi {
  display:flex; gap: 12px; align-items:center; padding: 14px 16px; border-radius: 14px;
  background: var(--soft-2); border: 1px solid #e2e8f0;
}
.kpi .value { font-weight: 700; font-size: 22px; }
.kpi .label { color: var(--muted); }
hr { border-color: #e5e7eb; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ===========================
# --------- STORAGE ---------
# ===========================
DATA_DIR = Path(".")
FILES = {
    "users": DATA_DIR / "user_db.json",            # includes admin + attempts/blocked
    "lecturers": DATA_DIR / "lecturers.json",
    "exam_personnel": DATA_DIR / "exam_personnel.json",
    "subjects": DATA_DIR / "subjects.json",
    "questions": DATA_DIR / "questions.json",
    "exam_papers": DATA_DIR / "exam_papers.json",
}

DEFAULTS = {
    "users": {"admin": {"password": "admin123", "role": "admin", "attempts": 0, "blocked": False, "name": "Administrator"}},
    "lecturers": {},
    "exam_personnel": {},
    "subjects": {},
    "questions": {},
    "exam_papers": {"Set 1": {"Section A": [], "Section B": []}, "Set 2": {"Section A": [], "Section B": []}},
}

def load_json(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_files():
    for key, path in FILES.items():
        if not path.exists():
            save_json(path, DEFAULTS[key])

ensure_files()

# Accessors
def db_users(): return load_json(FILES["users"], DEFAULTS["users"])
def save_users(d): save_json(FILES["users"], d)

def db_lecturers(): return load_json(FILES["lecturers"], DEFAULTS["lecturers"])
def save_lecturers(d): save_json(FILES["lecturers"], d)

def db_exam_personnel(): return load_json(FILES["exam_personnel"], DEFAULTS["exam_personnel"])
def save_exam_personnel(d): save_json(FILES["exam_personnel"], d)

def db_subjects(): return load_json(FILES["subjects"], DEFAULTS["subjects"])
def save_subjects(d): save_json(FILES["subjects"], d)

def db_questions(): return load_json(FILES["questions"], DEFAULTS["questions"])
def save_questions(d): save_json(FILES["questions"], d)

def db_exam_papers(): return load_json(FILES["exam_papers"], DEFAULTS["exam_papers"])
def save_exam_papers(d): save_json(FILES["exam_papers"], d)

# ===========================
# ------- UTILITIES ---------
# ===========================
def card_header(title: str, emoji: str = "📦", badge: str | None = None):
    cols = st.columns([1, 4, 2])
    with cols[0]:
        st.write(f"## {emoji}")
    with cols[1]:
        st.write(f"### {title}")
    with cols[2]:
        if badge:
            st.markdown(f'<span class="badge">{badge}</span>', unsafe_allow_html=True)

def require_auth():
    if "auth" not in st.session_state or not st.session_state["auth"].get("logged_in", False):
        st.warning("You are not logged in.")
        st.stop()

def reset_attempts(username: str):
    users = db_users()
    if username in users:
        users[username]["attempts"] = 0
        users[username]["blocked"] = False
        save_users(users)

def try_login(username: str, password: str) -> bool:
    users = db_users()
    all_users = {**users, **db_lecturers(), **db_exam_personnel()}  # roles in leaf DBs too
    if username not in all_users:
        st.error("User not found.")
        return False

    record = all_users[username]
    # Attempt/blocked tracking is stored in main users DB for all accounts.
    # Ensure a mirror exists:
    if username not in users:
        users[username] = {"password": record["password"], "role": record["role"], "attempts": 0, "blocked": False, "name": record.get("name", username)}
        save_users(users)
    users = db_users()
    mirror = users[username]

    if mirror.get("blocked", False):
        st.error("This account is blocked due to too many failed attempts. Contact admin.")
        return False

    if password == record["password"]:
        mirror["attempts"] = 0
        mirror["blocked"] = False
        save_users(users)
        st.session_state["auth"] = {"logged_in": True, "username": username, "role": record["role"], "name": record.get("name", username)}
        st.success("✅ Logged in successfully!")
        return True

    # wrong password
    mirror["attempts"] = mirror.get("attempts", 0) + 1
    if mirror["attempts"] >= 3:
        mirror["blocked"] = True
        st.error("Too many failed attempts. You have been blocked.")
    else:
        remaining = 3 - mirror["attempts"]
        st.error(f"Login failed. {remaining} attempt(s) left.")
    save_users(users)
    return False

def logout():
    st.session_state.pop("auth", None)
    st.rerun()

# ===========================
# ------- ADMIN UI ----------
# ===========================
def admin_dashboard():
    require_auth()
    auth = st.session_state["auth"]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"## 👑 Admin Dashboard — Welcome, **{auth.get('name', auth['username'])}**")
    cols = st.columns(3)
    with cols[0]:
        u = db_users()
        st.markdown(f'<div class="kpi"><div class="value">{len(u)}</div><div class="label">Users</div></div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="kpi"><div class="value">{len(db_lecturers())}</div><div class="label">Lecturers</div></div>', unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f'<div class="kpi"><div class="value">{len(db_exam_personnel())}</div><div class="label">Exam Personnel</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    tabs = st.tabs(["👤 Manage Users", "🎓 Lecturers", "🧪 Exam Personnel", "📚 Subjects", "❓ Questions", "📝 Exam Papers", "🔧 System"])
    # ----- Manage Users (block/unblock, change username/password) -----
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("User Controls", "👤", "security")
        users = db_users()
        usernames = list(users.keys())
        user_sel = st.selectbox("Select a user", usernames)
        if user_sel:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"Attempts: **{users[user_sel].get('attempts',0)}**")
            with col2:
                st.write(f"Blocked: **{users[user_sel].get('blocked', False)}**")
            with col3:
                if st.button("Reset Attempts / Unblock", key=f"reset_{user_sel}"):
                    reset_attempts(user_sel)
                    st.success("User unblocked & attempts reset.")
                    st.rerun()
            with col4:
                new_pass = st.text_input("Set New Password", type="password", key=f"np_{user_sel}")
                if st.button("Update Password", key=f"pw_{user_sel}") and new_pass:
                    # Update in both the canonical location (users or role-db) and mirror
                    if user_sel in users:
                        users[user_sel]["password"] = new_pass
                        save_users(users)
                    if user_sel in db_lecturers():
                        data = db_lecturers()
                        data[user_sel]["password"] = new_pass
                        save_lecturers(data)
                    if user_sel in db_exam_personnel():
                        data = db_exam_personnel()
                        data[user_sel]["password"] = new_pass
                        save_exam_personnel(data)
                    st.success("Password updated.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ----- Lecturers -----
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("Lecturers", "🎓", "accounts")
        lecturers = db_lecturers()
        st.write("### Add Lecturer")
        with st.form("add_lecturer"):
            lu = st.text_input("Username")
            lp = st.text_input("Password", type="password")
            lname = st.text_input("Name")
            laddr = st.text_input("Address")
            lphone = st.text_input("Contact Number")
            submitted = st.form_submit_button("Add Lecturer")
        if submitted:
            if lu.strip() == "" or lp.strip() == "":
                st.error("Username and password are required.")
            elif lu in lecturers:
                st.error("Username already exists.")
            else:
                lecturers[lu] = {"password": lp, "role": "lecturer", "profile": {"name": lname, "address": laddr, "contact_number": lphone}}
                save_lecturers(lecturers)
                # mirror in users DB
                users = db_users()
                users[lu] = {"password": lp, "role": "lecturer", "attempts": 0, "blocked": False, "name": lname or lu}
                save_users(users)
                st.success(f"Lecturer **{lu}** added.")

        st.write("### Existing Lecturers")
        if lecturers:
            colA, colB = st.columns([2, 1])
            with colA:
                st.json(lecturers)
            with colB:
                del_u = st.text_input("Delete Lecturer by Username")
                if st.button("Delete Lecturer", type="secondary"):
                    if del_u in lecturers:
                        lecturers.pop(del_u)
                        save_lecturers(lecturers)
                        users = db_users()
                        if del_u in users:
                            users.pop(del_u)
                            save_users(users)
                        st.success("Lecturer deleted.")
                        st.rerun()
                    else:
                        st.error("Lecturer not found.")
        else:
            st.info("No lecturers yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ----- Exam Personnel -----
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("Exam Personnel", "🧪", "accounts")
        ex = db_exam_personnel()
        st.write("### Add Exam Personnel")
        with st.form("add_ep"):
            eu = st.text_input("Username", key="ep_u")
            ep = st.text_input("Password", type="password", key="ep_p")
            ename = st.text_input("Name", key="ep_n")
            ephone = st.text_input("Contact Number", key="ep_c")
            submitted = st.form_submit_button("Add Exam Personnel")
        if submitted:
            if eu.strip() == "" or ep.strip() == "":
                st.error("Username and password are required.")
            elif eu in ex:
                st.error("Username already exists.")
            else:
                ex[eu] = {"password": ep, "role": "exam_personnel", "profile": {"name": ename, "contact_number": ephone}}
                save_exam_personnel(ex)
                users = db_users()
                users[eu] = {"password": ep, "role": "exam_personnel", "attempts": 0, "blocked": False, "name": ename or eu}
                save_users(users)
                st.success(f"Exam personnel **{eu}** added.")
        st.write("### Existing Exam Personnel")
        if ex:
            colA, colB = st.columns([2, 1])
            with colA:
                st.json(ex)
            with colB:
                del_u = st.text_input("Delete Exam Personnel by Username", key="ep_del")
                if st.button("Delete Exam Personnel", type="secondary"):
                    if del_u in ex:
                        ex.pop(del_u)
                        save_exam_personnel(ex)
                        users = db_users()
                        if del_u in users:
                            users.pop(del_u)
                            save_users(users)
                        st.success("Exam personnel deleted.")
                        st.rerun()
                    else:
                        st.error("User not found.")
        else:
            st.info("No exam personnel yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ----- Subjects -----
    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("Subjects", "📚", "curriculum")
        subjects = db_subjects()
        st.write("### Add Subject")
        with st.form("add_subject"):
            sname = st.text_input("Subject Name")
            topics_str = st.text_input("Topics (comma-separated, min 3)", placeholder="Loops, Functions, OOP")
            add_ok = st.form_submit_button("Add Subject")
        if add_ok:
            topics = [t.strip() for t in topics_str.split(",") if t.strip()]
            if len(topics) < 3:
                st.error("Minimum 3 topics required.")
            elif sname in subjects:
                st.error("Subject already exists.")
            else:
                subjects[sname] = topics
                save_subjects(subjects)
                st.success(f"Subject **{sname}** added with {len(topics)} topics.")

        st.write("### Existing Subjects")
        if subjects:
            st.json(subjects)
        else:
            st.info("No subjects yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ----- Questions -----
    with tabs[4]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("Questions", "❓", "bank")
        subjects = db_subjects()
        questions = db_questions()

        col1, col2 = st.columns(2)
        with col1:
            st.write("#### Add Question")
            with st.form("add_q"):
                subj = st.selectbox("Subject", options=[""] + list(subjects.keys()), index=0)
                topic = st.text_input("Topic")
                q_text = st.text_area("Question")
                ans_text = st.text_area("Answer")
                submit_q = st.form_submit_button("Add")
            if submit_q:
                if not subj or not topic or not q_text or not ans_text:
                    st.error("All fields required.")
                else:
                    questions.setdefault(subj, {}).setdefault(topic, []).append({"question": q_text, "answer": ans_text})
                    save_questions(questions)
                    st.success("Question added.")

        with col2:
            st.write("#### Update / View Questions")
            subj2 = st.selectbox("Subject (view)", options=[""] + list(questions.keys()))
            topic2 = None
            if subj2:
                topic2 = st.selectbox("Topic", options=[""] + list(questions[subj2].keys()))
            if subj2 and topic2:
                q_list = questions[subj2][topic2]
                if not q_list:
                    st.info("No questions in this topic.")
                else:
                    idx = st.number_input("Question Index", min_value=0, max_value=len(q_list)-1, step=1)
                    st.write("**Current Question:**")
                    st.write(q_list[idx]["question"])
                    st.write("**Current Answer:**")
                    st.write(q_list[idx]["answer"])
                    new_q = st.text_area("New Question", value=q_list[idx]["question"])
                    new_a = st.text_area("New Answer", value=q_list[idx]["answer"])
                    colU, colD = st.columns(2)
                    with colU:
                        if st.button("Update Question"):
                            q_list[idx] = {"question": new_q, "answer": new_a}
                            save_questions(questions)
                            st.success("Question updated.")
                    with colD:
                        if st.button("Delete Question", type="secondary"):
                            q_list.pop(idx)
                            save_questions(questions)
                            st.success("Question deleted.")
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ----- Exam Papers -----
    with tabs[5]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("Exam Papers", "📝", "assemble")
        papers = db_exam_papers()

        st.write("#### Add Question to Exam")
        with st.form("add_to_exam"):
            set_name = st.selectbox("Exam Set", options=list(papers.keys()))
            section = st.selectbox("Section", options=["Section A", "Section B"])
            qtext = st.text_area("Question text")
            ok = st.form_submit_button("Add to Exam Paper")
        if ok:
            limit = 5 if section == "Section A" else 3
            if len(papers[set_name][section]) >= limit:
                st.error(f"{section} already has maximum of {limit} questions.")
            else:
                papers[set_name][section].append(qtext)
                save_exam_papers(papers)
                st.success("Question added to exam paper.")

        st.write("#### Update Question in Exam")
        set2 = st.selectbox("Select Exam Set (update)", options=list(papers.keys()), key="set2")
        sec2 = st.selectbox("Section (update)", options=["Section A", "Section B"], key="sec2")
        if papers[set2][sec2]:
            idx2 = st.number_input("Question Index", min_value=0, max_value=len(papers[set2][sec2])-1, step=1, key="idx2")
            cur = papers[set2][sec2][idx2]
            newq = st.text_area("New Question", value=cur, key="newq")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Update Exam Question"):
                    papers[set2][sec2][idx2] = newq
                    save_exam_papers(papers)
                    st.success("Exam question updated.")
            with c2:
                if st.button("Delete Exam Question", type="secondary"):
                    papers[set2][sec2].pop(idx2)
                    save_exam_papers(papers)
                    st.success("Exam question deleted.")
                    st.rerun()
        else:
            st.info("No questions in this section.")

        st.write("#### View Exam Paper")
        set_view = st.selectbox("Exam Set (view)", options=list(papers.keys()), key="viewset")
        st.json(papers[set_view])
        st.markdown('</div>', unsafe_allow_html=True)

    # ----- System -----
    with tabs[6]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        card_header("System Tools", "🔧", "maintenance")
        if st.button("🔄 Reset Demo Data (Keeps Admin)"):
            # reset all except admin base users
            save_json(FILES["lecturers"], DEFAULTS["lecturers"])
            save_json(FILES["exam_personnel"], DEFAULTS["exam_personnel"])
            save_json(FILES["subjects"], DEFAULTS["subjects"])
            save_json(FILES["questions"], DEFAULTS["questions"])
            save_json(FILES["exam_papers"], DEFAULTS["exam_papers"])
            # keep admin, clean non-admin entries
            users = DEFAULTS["users"]
            save_json(FILES["users"], users)
            st.success("Reset completed.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ===========================
# ------ LECTURER UI --------
# ===========================
def lecturer_dashboard():
    require_auth()
    auth = st.session_state["auth"]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"## 🎓 Lecturer Dashboard — Hello, **{auth.get('name', auth['username'])}**")
    st.markdown('</div>', unsafe_allow_html=True)
    tabs = st.tabs(["❓ Manage Questions", "🔐 Account"])

    with tabs[0]:
        st.markdown('<div class="card soft">', unsafe_allow_html=True)
        subjects = db_subjects()
        questions = db_questions()

        st.write("### Add Question")
        with st.form("lec_add_q"):
            subj = st.selectbox("Subject", options=[""] + list(subjects.keys()))
            topic = st.text_input("Topic")
            q = st.text_area("Question")
            a = st.text_area("Answer")
            ok = st.form_submit_button("Add")
        if ok:
            if not subj or not topic or not q or not a:
                st.error("All fields required.")
            else:
                questions.setdefault(subj, {}).setdefault(topic, []).append({"question": q, "answer": a})
                save_questions(questions)
                st.success("Question added.")

        st.write("### View / Update")
        subj2 = st.selectbox("Subject (view)", options=[""] + list(questions.keys()), key="lec_s2")
        if subj2:
            topic2 = st.selectbox("Topic", options=[""] + list(questions[subj2].keys()), key="lec_t2")
            if topic2:
                q_list = questions[subj2][topic2]
                if q_list:
                    idx = st.number_input("Index", min_value=0, max_value=len(q_list)-1, step=1, key="lec_idx")
                    st.write("**Current Question:**")
                    st.write(q_list[idx]["question"])
                    st.write("**Current Answer:**")
                    st.write(q_list[idx]["answer"])
                    new_q = st.text_area("New Question", value=q_list[idx]["question"], key="lec_newq")
                    new_a = st.text_area("New Answer", value=q_list[idx]["answer"], key="lec_newa")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Update", key="lec_upd"):
                            q_list[idx] = {"question": new_q, "answer": new_a}
                            save_questions(questions)
                            st.success("Updated.")
                    with c2:
                        if st.button("Delete", key="lec_del", type="secondary"):
                            q_list.pop(idx)
                            save_questions(questions)
                            st.success("Deleted.")
                            st.rerun()
                else:
                    st.info("No questions here yet.")
            else:
                st.info("Pick a topic.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### Change Password / Username")
        col1, col2 = st.columns(2)
        with col1:
            new_pw = st.text_input("New Password", type="password")
            if st.button("Update Password"):
                # Update both lecturer DB & users mirror
                lec = db_lecturers()
                if auth["username"] in lec:
                    lec[auth["username"]]["password"] = new_pw
                    save_lecturers(lec)
                users = db_users()
                if auth["username"] in users:
                    users[auth["username"]]["password"] = new_pw
                    save_users(users)
                st.success("Password updated.")
        with col2:
            new_un = st.text_input("New Username")
            if st.button("Update Username"):
                if not new_un.strip():
                    st.error("Enter a valid username.")
                else:
                    # migrate keys in lecturer + users DBs
                    lec = db_lecturers()
                    if auth["username"] in lec:
                        lec[new_un] = lec.pop(auth["username"])
                        save_lecturers(lec)
                    users = db_users()
                    if auth["username"] in users:
                        users[new_un] = users.pop(auth["username"])
                        save_users(users)
                    st.success("Username updated. Please log in again.")
                    logout()
        st.markdown('</div>', unsafe_allow_html=True)

# ===========================
# --- EXAM PERSONNEL UI -----
# ===========================
def exam_personnel_dashboard():
    require_auth()
    auth = st.session_state["auth"]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"## 🧪 Exam Personnel — Welcome, **{auth.get('name', auth['username'])}**")
    st.markdown('</div>', unsafe_allow_html=True)

    tabs = st.tabs(["📝 Build Exam Papers", "🔐 Account"])

    # Build exam papers
    with tabs[0]:
        st.markdown('<div class="card soft">', unsafe_allow_html=True)
        papers = db_exam_papers()

        st.write("### Add Question to Exam")
        with st.form("ep_add"):
            set_name = st.selectbox("Exam Set", options=list(papers.keys()))
            section = st.selectbox("Section", options=["Section A", "Section B"])
            qtext = st.text_area("Question")
            ok = st.form_submit_button("Add")
        if ok:
            limit = 5 if section == "Section A" else 3
            if len(papers[set_name][section]) >= limit:
                st.error(f"{section} already at max ({limit}).")
            else:
                papers[set_name][section].append(qtext)
                save_exam_papers(papers)
                st.success("Added to paper.")

        st.write("### Update / View Paper")
        set2 = st.selectbox("Exam Set (update)", options=list(papers.keys()), key="ep_set2")
        sec2 = st.selectbox("Section (update)", options=["Section A", "Section B"], key="ep_sec2")
        if papers[set2][sec2]:
            idx2 = st.number_input("Index", min_value=0, max_value=len(papers[set2][sec2])-1, step=1, key="ep_idx2")
            current = papers[set2][sec2][idx2]
            newq = st.text_area("New Question", value=current, key="ep_newq")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Update Question", key="ep_upd"):
                    papers[set2][sec2][idx2] = newq
                    save_exam_papers(papers)
                    st.success("Updated.")
            with c2:
                if st.button("Delete Question", key="ep_del", type="secondary"):
                    papers[set2][sec2].pop(idx2)
                    save_exam_papers(papers)
                    st.success("Deleted.")
                    st.rerun()
        else:
            st.info("No questions in this section yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### Change Password / Username")
        col1, col2 = st.columns(2)
        with col1:
            new_pw = st.text_input("New Password", type="password", key="ep_pw")
            if st.button("Update Password", key="ep_pw_btn"):
                ep = db_exam_personnel()
                if auth["username"] in ep:
                    ep[auth["username"]]["password"] = new_pw
                    save_exam_personnel(ep)
                users = db_users()
                if auth["username"] in users:
                    users[auth["username"]]["password"] = new_pw
                    save_users(users)
                st.success("Password updated.")
        with col2:
            new_un = st.text_input("New Username", key="ep_un")
            if st.button("Update Username", key="ep_un_btn"):
                if not new_un.strip():
                    st.error("Enter a valid username.")
                else:
                    ep = db_exam_personnel()
                    if auth["username"] in ep:
                        ep[new_un] = ep.pop(auth["username"])
                        save_exam_personnel(ep)
                    users = db_users()
                    if auth["username"] in users:
                        users[new_un] = users.pop(auth["username"])
                        save_users(users)
                    st.success("Username updated. Please log in again.")
                    logout()
        st.markdown('</div>', unsafe_allow_html=True)

# ===========================
# ---------- AUTH -----------
# ===========================
def login_ui():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("## 🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Login"):
            try_login(username, password)
    with col2:
        st.caption("3 failed attempts will block the user. Admin can unblock from dashboard.")
    st.markdown('</div>', unsafe_allow_html=True)

# ===========================
# ---------- APP ------------
# ===========================
def navbar():
    st.write("")
    with st.container():
        cols = st.columns([6, 3, 3])
        with cols[0]:
            st.write("### 📚 Exam Management System")
        with cols[1]:
            if "auth" in st.session_state and st.session_state["auth"].get("logged_in"):
                st.write(f"**{st.session_state['auth']['username']}** — `{st.session_state['auth']['role']}`")
        with cols[2]:
            if "auth" in st.session_state and st.session_state["auth"].get("logged_in"):
                st.button("🚪 Logout", on_click=logout)

def main():
    navbar()
    if "auth" not in st.session_state or not st.session_state["auth"].get("logged_in", False):
        login_ui()
        st.info("Default admin login: **admin** / **admin123**")
        st.divider()
        with st.container():
            st.markdown('<div class="card soft">', unsafe_allow_html=True)
            st.write("### ✨ What you can do")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**👑 Admin**")
                st.markdown("- Manage users (block/unblock, reset attempts)\n- CRUD lecturers & exam personnel\n- Manage subjects, questions\n- Assemble exam papers")
            with c2:
                st.markdown("**🎓 Lecturer**")
                st.markdown("- Add / update / delete questions\n- Change password / username")
            with c3:
                st.markdown("**🧪 Exam Personnel**")
                st.markdown("- Add / edit exam paper questions\n- Enforce section limits\n- Change password / username")
            st.markdown('</div>', unsafe_allow_html=True)
        return

    role = st.session_state["auth"]["role"]
    if role == "admin":
        admin_dashboard()
    elif role == "lecturer":
        lecturer_dashboard()
    elif role == "exam_personnel":
        exam_personnel_dashboard()
    else:
        st.error("Unknown role.")

if __name__ == "__main__":
    main()
