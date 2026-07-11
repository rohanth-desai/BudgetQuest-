import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import date

# ---------- setup ----------

st.set_page_config(page_title="BudgetQuest", page_icon="💰", layout="centered")

DATA_DIR = "user_data"
os.makedirs(DATA_DIR, exist_ok=True)
LEADERBOARD_FILE = os.path.join(DATA_DIR, "leaderboard.json")

CATEGORIES = ["Food", "Travel", "Entertainment", "Education", "Other"]
CATEGORY_COLORS = {
    "Food": "#4FD1A5",
    "Travel": "#5FA8D3",
    "Entertainment": "#E0A458",
    "Education": "#C084FC",
    "Other": "#94A3A8",
}

CHALLENGES = [
    {"id": "no_spend_day", "label": "No-Spend Day", "desc": "Go one full day without logging an expense.", "points": 10},
    {"id": "under_budget_week", "label": "Under Budget This Week", "desc": "Keep 7 days of spending under your weekly share of budget.", "points": 20},
    {"id": "log_streak", "label": "5-Day Logging Streak", "desc": "Record an expense on 5 different days.", "points": 10},
    {"id": "save_10", "label": "Save 10% of Budget", "desc": "End the month having spent at most 90% of your budget.", "points": 25},
]

# ---------- storage helpers ----------

def user_file(username):
    return os.path.join(DATA_DIR, f"{username}.json")

def load_user_data(username):
    path = user_file(username)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"expenses": [], "budget": 6000, "challenges": {}}

def save_user_data(username, data):
    with open(user_file(username), "w") as f:
        json.dump(data, f, indent=2)

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    return {}

def save_leaderboard(board):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(board, f, indent=2)

def update_leaderboard(username, score, total_spent):
    board = load_leaderboard()
    board[username] = {"score": score, "total_spent": total_spent, "updated": str(date.today())}
    save_leaderboard(board)
    return board

# ---------- username gate ----------

if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.username:
    st.title("💰 BudgetQuest ")
    st.write("Pick a name — it's how friends will find you on the leaderboard.")
    name_input = st.text_input("Your name", placeholder="e.g. Aarav")
    if st.button("Open my ledger", type="primary"):
        if name_input.strip():
            st.session_state.username = name_input.strip()
            st.rerun()
    st.stop()

username = st.session_state.username
data = load_user_data(username)

# ---------- sidebar ----------

st.sidebar.title("💰 BudgetQuest ")
st.sidebar.caption(f"Logged in as **{username}**")
page = st.sidebar.radio("Go to", ["Dashboard", "Add Expense", "Budget", "Challenges", "Leaderboard"])
if st.sidebar.button("Switch user"):
    st.session_state.username = ""
    st.rerun()

# ---------- derived numbers ----------

df = pd.DataFrame(data["expenses"])
total_spent = df["amount"].sum() if not df.empty else 0
budget = data["budget"]
remaining = budget - total_spent
pct_used = min(100, (total_spent / budget * 100)) if budget > 0 else 0
savings_rate = max(0, round((budget - total_spent) / budget * 100)) if budget > 0 else 0

completed = data["challenges"]
completed_points = sum(c["points"] for c in CHALLENGES if completed.get(c["id"]))
my_score = savings_rate + completed_points

update_leaderboard(username, my_score, total_spent)

# ---------- Dashboard ----------

if page == "Dashboard":
    st.title("Dashboard")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Spent", f"₹{total_spent:,.0f}", delta=f"₹{remaining:,.0f} remaining" if remaining >= 0 else f"₹{abs(remaining):,.0f} over budget", delta_color="normal" if remaining >= 0 else "inverse")
        st.progress(pct_used / 100)
    with col2:
        st.metric("Monthly Budget", f"₹{budget:,.0f}")
        st.metric("Budget Saved", f"{savings_rate}%")

    st.subheader("Spending by Category")
    if not df.empty:
        cat_totals = df.groupby("category")["amount"].sum()
        fig, ax = plt.subplots()
        colors = [CATEGORY_COLORS.get(c, "#999") for c in cat_totals.index]
        ax.pie(cat_totals, labels=cat_totals.index, autopct="%1.0f%%", colors=colors, textprops={"fontsize": 9})
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.caption("Nothing logged yet.")

    st.subheader("Recent Daily Spending")
    if not df.empty:
        daily = df.groupby("date")["amount"].sum().sort_index().tail(10)
        st.bar_chart(daily)
    else:
        st.caption("Log expenses to see a trend.")

    st.subheader("Ledger")
    if not df.empty:
        show = df.sort_values("date", ascending=False)[["date", "category", "note", "amount"]]
        st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.caption("No entries yet — add your first expense.")

# ---------- Add Expense ----------

elif page == "Add Expense":
    st.title("Add Expense")
    with st.form("add_expense", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        category = st.selectbox("Category", CATEGORIES)
        note = st.text_input("Note (optional)", placeholder="e.g. Canteen lunch")
        entry_date = st.date_input("Date", value=date.today())
        submitted = st.form_submit_button("Add to Ledger", type="primary")

        if submitted and amount > 0:
            data["expenses"].append({
                "amount": float(amount),
                "category": category,
                "note": note,
                "date": str(entry_date),
            })
            save_user_data(username, data)
            st.success(f"Added ₹{amount:,.0f} under {category}.")
            st.rerun()

# ---------- Budget ----------

elif page == "Budget":
    st.title("Budget")
    new_budget = st.number_input("Monthly budget (₹)", min_value=0.0, value=float(budget), step=100.0)
    if new_budget != budget:
        data["budget"] = new_budget
        save_user_data(username, data)
        st.rerun()

    if remaining < 0:
        st.error(f"You're ₹{abs(remaining):,.0f} over your monthly budget.")
    else:
        st.success(f"You're on track with ₹{remaining:,.0f} remaining.")

    st.subheader("Category Breakdown")
    if not df.empty:
        cat_totals = df.groupby("category")["amount"].sum()
        for cat in CATEGORIES:
            val = cat_totals.get(cat, 0)
            if val > 0:
                pct = min(100, val / budget * 100) if budget > 0 else 0
                st.write(f"**{cat}** — ₹{val:,.0f}")
                st.progress(pct / 100)
    else:
        st.caption("Log some expenses to see the split.")

# ---------- Challenges ----------

elif page == "Challenges":
    st.title("Challenges")
    st.caption("Mark a challenge complete once you've genuinely done it — each adds points to your leaderboard score.")

    for c in CHALLENGES:
        done = completed.get(c["id"], False)
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"**{c['label']}**  `+{c['points']} pts`")
            st.caption(c["desc"])
        with col2:
            new_state = st.checkbox("Done", value=done, key=c["id"])
        if new_state != done:
            data["challenges"][c["id"]] = new_state
            save_user_data(username, data)
            st.rerun()

    st.divider()
    col1, col2 = st.columns(2)
    distinct_days = df["date"].nunique() if not df.empty else 0
    col1.metric("Days Logged", distinct_days)
    col2.metric("Budget Saved", f"{savings_rate}%")

# ---------- Leaderboard ----------

elif page == "Leaderboard":
    st.title("Friends Leaderboard")
    st.caption("Everyone who opens this app on this computer (or shared folder) shows up here.")

    board = load_leaderboard()
    if not board:
        st.caption("No one on the board yet — you're first.")
    else:
        ranked = sorted(board.items(), key=lambda x: x[1]["score"], reverse=True)
        rows = []
        for i, (name, info) in enumerate(ranked):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            rows.append({"Rank": medal, "Name": name + (" (you)" if name == username else ""), "Score": f"{info['score']} pts"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.info(f"Your current score is *{my_score} pts* — from budget savings and completed challenges.")
    