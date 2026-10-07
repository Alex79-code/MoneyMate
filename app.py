from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection
from datetime import datetime


app = Flask(__name__)

app.secret_key = "moneymate-secret-key"


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return """
    <h1>Welcome to MoneyMate!</h1>

    <p>Your personal finance manager.</p>

    <a href="/about">About</a> |
    <a href="/dashboard">Dashboard</a> |
    <a href="/register">Register</a> |
    <a href="/login">Login</a> |
    <a href="/add-income">Add Income</a> |
    <a href="/add-expense">Add Expense</a> |
    <a href="/budget">Budget</a>
    """


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    return """
    <h1>About MoneyMate</h1>

    <p>
        MoneyMate helps you manage your income and expenses.
    </p>

    <a href="/">Home</a> |
    <a href="/dashboard">Dashboard</a>
    """


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name:

            return """
            <h1>MoneyMate</h1>
            <p>Please enter your name.</p>
            <a href="/register">Try Again</a>
            """, 400

        if not email:

            return """
            <h1>MoneyMate</h1>
            <p>Please enter your email.</p>
            <a href="/register">Try Again</a>
            """, 400

        if not password:

            return """
            <h1>MoneyMate</h1>
            <p>Please enter your password.</p>
            <a href="/register">Try Again</a>
            """, 400

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Email already registered.
                </p>

                <a href="/register">
                    Try Again
                </a>
                """

            password_hash = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash
                )
                VALUES (%s, %s, %s)
                """,
                (
                    name,
                    email,
                    password_hash
                )
            )

            connection.commit()

            return """
            <h1>Registration Successful!</h1>

            <p>
                Your MoneyMate account has been created.
            </p>

            <a href="/login">
                Go to Login
            </a>
            """

        except Exception:

            app.logger.exception(
                "Could not register user"
            )

            return """
            <h1>MoneyMate</h1>

            <p>
                Unable to create account.
            </p>

            <a href="/register">
                Try Again
            </a>
            """, 500

        finally:

            if cursor is not None:
                cursor.close()

            if connection is not None:
                connection.close()

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please enter email and password.
            </p>

            <a href="/login">
                Try Again
            </a>
            """, 400

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password_hash
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user is None:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Invalid email or password.
                </p>

                <a href="/login">
                    Try Again
                </a>
                """

            stored_password_hash = user[3]

            if not check_password_hash(
                stored_password_hash,
                password
            ):

                return """
                <h1>MoneyMate</h1>

                <p>
                    Invalid email or password.
                </p>

                <a href="/login">
                    Try Again
                </a>
                """

            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]

            return redirect(
                url_for("dashboard")
            )

        except Exception:

            app.logger.exception(
                "Could not login user"
            )

            return """
            <h1>MoneyMate</h1>

            <p>
                Unable to login.
            </p>

            <a href="/login">
                Try Again
            </a>
            """, 500

        finally:

            if cursor is not None:
                cursor.close()

            if connection is not None:
                connection.close()

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    search = request.args.get(
        "search",
        ""
    ).strip()

    transaction_type = request.args.get(
        "type",
        "All"
    )

    from_date = request.args.get(
        "from_date",
        ""
    ).strip()

    to_date = request.args.get(
        "to_date",
        ""
    ).strip()

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        # =================================================
        # TOTAL INCOME
        # =================================================

        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM income
            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_income = cursor.fetchone()[0]

        # =================================================
        # TOTAL EXPENSES
        # =================================================

        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_expenses = cursor.fetchone()[0]

        # =================================================
        # BALANCE
        # =================================================

        balance = total_income - total_expenses

        # =================================================
        # EXPENSE ANALYTICS
        # =================================================

        cursor.execute(
            """
            SELECT
                category,
                COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = %s
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id,)
        )

        expense_by_category = cursor.fetchall()

        # =================================================
        # BUDGET INFORMATION
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                month_year,
                budget_amount
            FROM budgets
            WHERE user_id = %s
            ORDER BY month_year DESC
            """,
            (user_id,)
        )

        budget_rows = cursor.fetchall()

        budgets = []

        for budget_row in budget_rows:

            budget_id = budget_row[0]
            month_year = budget_row[1]
            budget_amount = float(budget_row[2])

            # -------------------------------------------------
            # Calculate exact start and end dates
            # for the selected budget month
            # -------------------------------------------------

            try:

                budget_start_date = datetime.strptime(
                    month_year,
                    "%Y-%m"
                ).date()

                if budget_start_date.month == 12:

                    budget_end_date = datetime(
                        budget_start_date.year + 1,
                        1,
                        1
                    ).date()

                else:

                    budget_end_date = datetime(
                        budget_start_date.year,
                        budget_start_date.month + 1,
                        1
                    ).date()

            except ValueError:

                budget_start_date = None
                budget_end_date = None

            # -------------------------------------------------
            # Calculate expenses for this exact budget month
            # -------------------------------------------------

            if (
                budget_start_date is not None
                and budget_end_date is not None
            ):

                cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(amount), 0)
                    FROM expenses
                    WHERE user_id = %s
                    AND expense_date >= %s
                    AND expense_date < %s
                    """,
                    (
                        user_id,
                        budget_start_date,
                        budget_end_date
                    )
                )

                spent = cursor.fetchone()[0]

            else:

                spent = 0

            if spent is None:
                spent = 0

            spent = float(spent)

            # -------------------------------------------------
            # Calculate remaining amount
            # -------------------------------------------------

            remaining = budget_amount - spent

            # -------------------------------------------------
            # Calculate percentage used
            # -------------------------------------------------

            if budget_amount > 0:

                percentage = (
                    spent / budget_amount
                ) * 100

            else:

                percentage = 0

            # -------------------------------------------------
            # Budget warning system
            # -------------------------------------------------

            if percentage >= 100:

                budget_status = "Over Budget"

                budget_status_message = (
                    "🚨 You have exceeded your monthly budget!"
                )

                budget_status_class = "danger"

            elif percentage >= 80:

                budget_status = "Approaching Limit"

                budget_status_message = (
                    "⚠️ You are approaching your monthly budget limit."
                )

                budget_status_class = "warning"

            else:

                budget_status = "Budget Healthy"

                budget_status_message = (
                    "✅ Your spending is within a healthy range."
                )

                budget_status_class = "success"

            # -------------------------------------------------
            # Progress bar maximum = 100%
            # -------------------------------------------------

            progress_percentage = percentage

            if progress_percentage > 100:

                progress_percentage = 100

            budgets.append(
                {
                    "id": budget_id,
                    "month_year": month_year,
                    "budget_amount": budget_amount,
                    "spent": spent,
                    "remaining": remaining,
                    "percentage": percentage,
                    "progress_percentage": progress_percentage,
                    "status": budget_status,
                    "status_message": budget_status_message,
                    "status_class": budget_status_class
                }
            )

        # =================================================
        # INCOME QUERY
        # =================================================

        income_query = """
            SELECT
                'Income' AS type,
                id,
                source AS details,
                amount,
                income_date AS transaction_date
            FROM income
            WHERE user_id = %s
        """

        # =================================================
        # EXPENSE QUERY
        # =================================================

        expense_query = """
            SELECT
                'Expense' AS type,
                id,
                category AS details,
                amount,
                expense_date AS transaction_date
            FROM expenses
            WHERE user_id = %s
        """

        income_params = [user_id]
        expense_params = [user_id]

        # =================================================
        # SEARCH FILTER
        # =================================================

        if search:

            income_query += """
                AND (
                    source LIKE %s
                    OR description LIKE %s
                )
            """

            expense_query += """
                AND (
                    category LIKE %s
                    OR description LIKE %s
                )
            """

            search_value = "%" + search + "%"

            income_params.extend([
                search_value,
                search_value
            ])

            expense_params.extend([
                search_value,
                search_value
            ])

        # =================================================
        # FROM DATE
        # =================================================

        if from_date:

            income_query += """
                AND income_date >= %s
            """

            expense_query += """
                AND expense_date >= %s
            """

            income_params.append(from_date)
            expense_params.append(from_date)

        # =================================================
        # TO DATE
        # =================================================

        if to_date:

            income_query += """
                AND income_date <= %s
            """

            expense_query += """
                AND expense_date <= %s
            """

            income_params.append(to_date)
            expense_params.append(to_date)

        # =================================================
        # TRANSACTION TYPE
        # =================================================

        if transaction_type == "Income":

            final_query = income_query + """
                ORDER BY transaction_date DESC
            """

            final_params = income_params

        elif transaction_type == "Expense":

            final_query = expense_query + """
                ORDER BY transaction_date DESC
            """

            final_params = expense_params

        else:

            final_query = """
                SELECT *
                FROM
                (
                    %s

                    UNION ALL

                    %s
                ) AS all_transactions

                ORDER BY transaction_date DESC
            """ % (
                income_query,
                expense_query
            )

            final_params = (
                income_params +
                expense_params
            )

        # =================================================
        # GET TRANSACTIONS
        # =================================================

        cursor.execute(
            final_query,
            tuple(final_params)
        )

        transactions = cursor.fetchall()

        # =================================================
        # DEBUG INFORMATION
        # =================================================

        print()
        print("========================================")
        print("MONEYMATE DASHBOARD")
        print("========================================")
        print("Logged-in User ID:", user_id)
        print("Total Income:", total_income)
        print("Total Expenses:", total_expenses)
        print("Balance:", balance)
        print("Expense By Category:", expense_by_category)
        print("Budgets:", budgets)
        print("Search:", search)
        print("Transaction Type:", transaction_type)
        print("From Date:", from_date)
        print("To Date:", to_date)
        print("Filtered Transactions:", transactions)
        print("========================================")
        print()

        # =================================================
        # SEND DATA TO HTML
        # =================================================

        return render_template(
            "dashboard.html",
            user_name=session.get(
                "user_name",
                "User"
            ),
            total_income=total_income,
            total_expenses=total_expenses,
            balance=balance,
            expense_by_category=expense_by_category,
            transactions=transactions,
            search=search,
            transaction_type=transaction_type,
            from_date=from_date,
            to_date=to_date,
            budgets=budgets
        )

    except Exception:

        app.logger.exception(
            "Could not load dashboard"
        )

        return """
        <h1>MoneyMate</h1>

        <p>
            Unable to load dashboard data.
        </p>

        <a href="/dashboard">
            Try Again
        </a>
        """, 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =========================================================
# ADD INCOME
# =========================================================

@app.route(
    "/add-income",
    methods=["GET", "POST"]
)
def add_income():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        source = request.form.get(
            "source",
            ""
        ).strip()

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        income_date = request.form.get(
            "income_date",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not source:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please enter an income source.
            </p>

            <a href="/add-income">
                Try Again
            </a>
            """, 400

        if not amount:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please enter an income amount.
            </p>

            <a href="/add-income">
                Try Again
            </a>
            """, 400

        try:

            amount_value = float(amount)

        except ValueError:

            return """
            <h1>MoneyMate</h1>

            <p>
                Amount must be a valid number.
            </p>

            <a href="/add-income">
                Try Again
            </a>
            """, 400

        if amount_value <= 0:

            return """
            <h1>MoneyMate</h1>

            <p>
                Income amount must be greater than zero.
            </p>

            <a href="/add-income">
                Try Again
            </a>
            """, 400

        if not income_date:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please select an income date.
            </p>

            <a href="/add-income">
                Try Again
            </a>
            """, 400

        user_id = session["user_id"]

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO income
                (
                    user_id,
                    source,
                    amount,
                    income_date,
                    description
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    source,
                    amount_value,
                    income_date,
                    description
                )
            )

            connection.commit()

            return redirect(
                url_for("dashboard")
            )

        except Exception:

            app.logger.exception(
                "Could not add income"
            )

            return """
            <h1>MoneyMate</h1>

            <p>
                Unable to save income.
            </p>

            <a href="/add-income">
                Try Again
            </a>
            """, 500

        finally:

            if cursor is not None:
                cursor.close()

            if connection is not None:
                connection.close()

    return render_template(
        "add_income.html"
    )


# =========================================================
# EDIT INCOME
# =========================================================

@app.route(
    "/edit-income/<int:income_id>",
    methods=["GET", "POST"]
)
def edit_income(income_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        if request.method == "POST":

            source = request.form.get(
                "source",
                ""
            ).strip()

            amount = request.form.get(
                "amount",
                ""
            ).strip()

            income_date = request.form.get(
                "income_date",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            if not source:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please enter an income source.
                </p>

                <a href="/edit-income/%s">
                    Try Again
                </a>
                """ % income_id, 400

            if not amount:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please enter an income amount.
                </p>

                <a href="/edit-income/%s">
                    Try Again
                </a>
                """ % income_id, 400

            try:

                amount_value = float(amount)

            except ValueError:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Amount must be a valid number.
                </p>

                <a href="/edit-income/%s">
                    Try Again
                </a>
                """ % income_id, 400

            if amount_value <= 0:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Income amount must be greater than zero.
                </p>

                <a href="/edit-income/%s">
                    Try Again
                </a>
                """ % income_id, 400

            if not income_date:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please select an income date.
                </p>

                <a href="/edit-income/%s">
                    Try Again
                </a>
                """ % income_id, 400

            cursor.execute(
                """
                UPDATE income

                SET
                    source = %s,
                    amount = %s,
                    income_date = %s,
                    description = %s

                WHERE id = %s

                AND user_id = %s
                """,
                (
                    source,
                    amount_value,
                    income_date,
                    description,
                    income_id,
                    user_id
                )
            )

            connection.commit()

            return redirect(
                url_for("dashboard")
            )

        cursor.execute(
            """
            SELECT
                source,
                amount,
                income_date,
                description

            FROM income

            WHERE id = %s

            AND user_id = %s
            """,
            (
                income_id,
                user_id
            )
        )

        income = cursor.fetchone()

        if income is None:

            return """
            <h1>MoneyMate</h1>

            <p>
                Income record not found.
            </p>

            <a href="/dashboard">
                Back to Dashboard
            </a>
            """, 404

        return render_template(
            "edit_income.html",
            income=income
        )

    except Exception:

        app.logger.exception(
            "Could not edit income"
        )

        return """
        <h1>MoneyMate</h1>

        <p>
            Unable to edit income.
        </p>

        <a href="/dashboard">
            Back to Dashboard
        </a>
        """, 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route(
    "/add-expense",
    methods=["GET", "POST"]
)
def add_expense():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        category = request.form.get(
            "category",
            ""
        ).strip()

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        expense_date = request.form.get(
            "expense_date",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not category:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please select an expense category.
            </p>

            <a href="/add-expense">
                Try Again
            </a>
            """, 400

        if not amount:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please enter an expense amount.
            </p>

            <a href="/add-expense">
                Try Again
            </a>
            """, 400

        try:

            amount_value = float(amount)

        except ValueError:

            return """
            <h1>MoneyMate</h1>

            <p>
                Amount must be a valid number.
            </p>

            <a href="/add-expense">
                Try Again
            </a>
            """, 400

        if amount_value <= 0:

            return """
            <h1>MoneyMate</h1>

            <p>
                Expense amount must be greater than zero.
            </p>

            <a href="/add-expense">
                Try Again
            </a>
            """, 400

        if not expense_date:

            return """
            <h1>MoneyMate</h1>

            <p>
                Please select an expense date.
            </p>

            <a href="/add-expense">
                Try Again
            </a>
            """, 400

        user_id = session["user_id"]

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO expenses
                (
                    user_id,
                    category,
                    amount,
                    expense_date,
                    description
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    category,
                    amount_value,
                    expense_date,
                    description
                )
            )

            connection.commit()

            return redirect(
                url_for("dashboard")
            )

        except Exception:

            app.logger.exception(
                "Could not add expense"
            )

            return """
            <h1>MoneyMate</h1>

            <p>
                Unable to save expense.
            </p>

            <a href="/add-expense">
                Try Again
            </a>
            """, 500

        finally:

            if cursor is not None:
                cursor.close()

            if connection is not None:
                connection.close()

    return render_template(
        "add_expense.html"
    )


# =========================================================
# EDIT EXPENSE
# =========================================================

@app.route(
    "/edit-expense/<int:expense_id>",
    methods=["GET", "POST"]
)
def edit_expense(expense_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        if request.method == "POST":

            category = request.form.get(
                "category",
                ""
            ).strip()

            amount = request.form.get(
                "amount",
                ""
            ).strip()

            expense_date = request.form.get(
                "expense_date",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            if not category:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please select an expense category.
                </p>

                <a href="/edit-expense/%s">
                    Try Again
                </a>
                """ % expense_id, 400

            if not amount:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please enter an expense amount.
                </p>

                <a href="/edit-expense/%s">
                    Try Again
                </a>
                """ % expense_id, 400

            try:

                amount_value = float(amount)

            except ValueError:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Amount must be a valid number.
                </p>

                <a href="/edit-expense/%s">
                    Try Again
                </a>
                """ % expense_id, 400

            if amount_value <= 0:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Expense amount must be greater than zero.
                </p>

                <a href="/edit-expense/%s">
                    Try Again
                </a>
                """ % expense_id, 400

            if not expense_date:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please select an expense date.
                </p>

                <a href="/edit-expense/%s">
                    Try Again
                </a>
                """ % expense_id, 400

            cursor.execute(
                """
                UPDATE expenses

                SET
                    category = %s,
                    amount = %s,
                    expense_date = %s,
                    description = %s

                WHERE id = %s

                AND user_id = %s
                """,
                (
                    category,
                    amount_value,
                    expense_date,
                    description,
                    expense_id,
                    user_id
                )
            )

            connection.commit()

            return redirect(
                url_for("dashboard")
            )

        cursor.execute(
            """
            SELECT
                category,
                amount,
                expense_date,
                description

            FROM expenses

            WHERE id = %s

            AND user_id = %s
            """,
            (
                expense_id,
                user_id
            )
        )

        expense = cursor.fetchone()

        if expense is None:

            return """
            <h1>MoneyMate</h1>

            <p>
                Expense record not found.
            </p>

            <a href="/dashboard">
                Back to Dashboard
            </a>
            """, 404

        return render_template(
            "edit_expense.html",
            expense=expense
        )

    except Exception:

        app.logger.exception(
            "Could not edit expense"
        )

        return """
        <h1>MoneyMate</h1>

        <p>
            Unable to edit expense.
        </p>

        <a href="/dashboard">
            Back to Dashboard
        </a>
        """, 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =========================================================
# DELETE INCOME
# =========================================================

@app.route(
    "/delete-income/<int:income_id>",
    methods=["POST"]
)
def delete_income(income_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM income

            WHERE id = %s

            AND user_id = %s
            """,
            (
                income_id,
                user_id
            )
        )

        connection.commit()

        return redirect(
            url_for("dashboard")
        )

    except Exception:

        app.logger.exception(
            "Could not delete income"
        )

        return """
        <h1>MoneyMate</h1>

        <p>
            Unable to delete income.
        </p>

        <a href="/dashboard">
            Back to Dashboard
        </a>
        """, 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =========================================================
# DELETE EXPENSE
# =========================================================

@app.route(
    "/delete-expense/<int:expense_id>",
    methods=["POST"]
)
def delete_expense(expense_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM expenses

            WHERE id = %s

            AND user_id = %s
            """,
            (
                expense_id,
                user_id
            )
        )

        connection.commit()

        return redirect(
            url_for("dashboard")
        )

    except Exception:

        app.logger.exception(
            "Could not delete expense"
        )

        return """
        <h1>MoneyMate</h1>

        <p>
            Unable to delete expense.
        </p>

        <a href="/dashboard">
            Back to Dashboard
        </a>
        """, 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =========================================================
# BUDGET MANAGEMENT
# =========================================================

@app.route(
    "/budget",
    methods=["GET", "POST"]
)
def budget():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        # =================================================
        # SAVE / UPDATE BUDGET
        # =================================================

        if request.method == "POST":

            month_year = request.form.get(
                "month_year",
                ""
            ).strip()

            budget_amount = request.form.get(
                "budget_amount",
                ""
            ).strip()

            if not month_year:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please select a month.
                </p>

                <a href="/budget">
                    Try Again
                </a>
                """, 400

            if not budget_amount:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Please enter a budget amount.
                </p>

                <a href="/budget">
                    Try Again
                </a>
                """, 400

            try:

                budget_value = float(
                    budget_amount
                )

            except ValueError:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Budget amount must be a valid number.
                </p>

                <a href="/budget">
                    Try Again
                </a>
                """, 400

            if budget_value <= 0:

                return """
                <h1>MoneyMate</h1>

                <p>
                    Budget amount must be greater than zero.
                </p>

                <a href="/budget">
                    Try Again
                </a>
                """, 400

            cursor.execute(
                """
                SELECT
                    id
                FROM budgets
                WHERE user_id = %s
                AND month_year = %s
                """,
                (
                    user_id,
                    month_year
                )
            )

            existing_budget = cursor.fetchone()

            if existing_budget:

                cursor.execute(
                    """
                    UPDATE budgets

                    SET
                        budget_amount = %s

                    WHERE user_id = %s
                    AND month_year = %s
                    """,
                    (
                        budget_value,
                        user_id,
                        month_year
                    )
                )

            else:

                cursor.execute(
                    """
                    INSERT INTO budgets
                    (
                        user_id,
                        month_year,
                        budget_amount
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        user_id,
                        month_year,
                        budget_value
                    )
                )

            connection.commit()

            return redirect(
                url_for("budget")
            )

        # =================================================
        # GET USER BUDGETS
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                month_year,
                budget_amount
            FROM budgets
            WHERE user_id = %s
            ORDER BY month_year DESC
            """,
            (user_id,)
        )

        budgets = cursor.fetchall()

        return render_template(
            "budget.html",
            budgets=budgets
        )

    except Exception:

        app.logger.exception(
            "Could not manage budget"
        )

        return """
        <h1>MoneyMate</h1>

        <p>
            Unable to manage budget.
        </p>

        <a href="/dashboard">
            Back to Dashboard
        </a>
        """, 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )