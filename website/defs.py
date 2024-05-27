import datetime
import os

from forex_python.converter import CurrencyRates
from datetime import date
import time
from flask import current_app, url_for
from flask_login import current_user
from sqlalchemy import asc, desc
from website import models
from website.constants import TRANSACTION_CATEGORIES, GOAL_CATEGORIES
from website.models import *
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def get_all_transactions():
    transactions = Transaction.query.filter_by(id=current_user.id).order_by(desc(Transaction.date)).all()

    tran_li = []

    for transaction in transactions:
        tran_li.append({
            'transaction_id': transaction.transaction_id,
            'amount': transaction.amount,
            'transaction_type': transaction.transaction_type,
            'date': transaction.date,
            'target': transaction.target,
            'category': Category.query.filter_by(category_id=transaction.category_id).first().name

        })


    return tran_li

def get_last3_transactions() -> list:
    last_transactions = Transaction.query.filter_by(id=current_user.id).order_by(desc(Transaction.date)).limit(3).all()
    
    return last_transactions

def create_user_categories():
    categories = Category.query.filter_by(id=current_user.id, type="transaction").all()
    if len(categories) == 0:
        for name in TRANSACTION_CATEGORIES:
            new_category = Category(name=name, id=current_user.id, type="transaction")
            db.session.add(new_category)
            
        db.session.commit()
    else:
        pass

    goal_categories = db.session.query(Category).filter_by(id = current_user.id, type = "goal").all()
    if goal_categories:
        pass
    else:

        for category in GOAL_CATEGORIES:

            new_category = Category(name=category, id=current_user.id, type="goal")
            db.session.add(new_category)
        
        db.session.commit()

def get_transaction_categories():
    categories = Category.query.filter_by(id=current_user.id, type="transaction").all()

    cat_li = []
    for category in categories:
        cat_li.append({
            'category_id': category.category_id,
            'name': category.name
        })

    return cat_li

def create_notif(title: str, date: str, description: str, type: str):
    date_str = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    new_notif_record = Notification(title = title, date = date_str, description = description, type = type, id = current_user.id, state= "new")
    db.session.add(new_notif_record)
    db.session.commit()

def get_new_notifs() -> list:
    
    notifications = Notification.query.filter_by(id=current_user.id, state="new").order_by(desc(Notification.date)).all()
    new_notifs = []
    for notif in notifications:
        new_notifs.append(
            {
                'notif_id': notif.notification_id,
                'title': notif.title,
                'date': notif.date,
                'description': notif.description,
                'type': notif.type,
                'state': notif.state
            }
        )

    return new_notifs

def get_old_notifs() -> list:
    notifications = Notification.query.filter_by(id=current_user.id, state="old").order_by(desc(Notification.date)).all()
    
    old_notifs = []
    for notif in notifications:
        old_notifs.append(
            {
                'notif_id': notif.notification_id,
                'title': notif.title,
                'date': notif.date,
                'description': notif.description,
                'type': notif.type,
                'state': notif.state
            }
        )

    return old_notifs


def create_balance():
    balance = Balance.query.filter_by(id=current_user.id, category='main').first()
    if balance is None:
        print("balance is none")
        new_balance_record = Balance(id = current_user.id, amount = 0, category='main')
        db.session.add(new_balance_record)
        db.session.commit()
    else:
        pass

def get_first_balance_amount() -> int:
    balance = Balance.query.filter_by(id=current_user.id, category='main').first()
    amount = balance.amount
    return amount

def get_user_balance() -> Balance:
    """Retrieve the balance of the current user."""
    balance = Balance.query.filter_by(id=current_user.id, category='main').first()

    return balance

def add_to_balance(amount: int, type: str):
    print("add to balance func")
    balance = get_user_balance()
    if balance is None:
        create_balance()
    
    if type == "Income":
        balance.amount += amount
    elif type == "Expense":
        balance.amount -= amount

    db.session.commit()

def recurr_check():
    current_date =  datetime.datetime.now().date()
    recurr_transactions = models.Recurr_Transactions.query.filter_by(id=current_user.id).all()

    if recurr_transactions:

        for recurr_transaction in recurr_transactions:
            next_date = recurr_transaction.next_date

            next_date = datetime.datetime.strptime(str(next_date), '%Y-%m-%d')
            next_date = next_date.date()
            
            if next_date > current_date:
                continue
            else:
                while next_date <= current_date:
                    if recurr_transaction.rate == "Weekly":
                        new_record = models.Transaction(amount=recurr_transaction.amount, target = recurr_transaction.target, transaction_type=recurr_transaction.type, date=next_date, id = recurr_transaction.id, category_id=recurr_transaction.category_id, recurr_transaction_id = recurr_transaction.id)
                        add_to_balance(recurr_transaction.amount, recurr_transaction.type)
                        create_notif(recurr_transaction.target, str(next_date), "Your recurring transaction has been completed", 'positive' if recurr_transaction.type == "Income" else 'negative')
                        old_date = next_date
                        next_date = next_date + datetime.timedelta(days=7)
                        recurr_transaction.next_date = next_date
                        db.session.add(new_record)
                        db.session.commit()
                        create_receipt(new_record.transaction_id, recurr_transaction.target, recurr_transaction.amount, recurr_transaction.type, str(old_date), recurr_transaction.category_id)

                    elif recurr_transaction.rate == "Monthly":
                        new_record = models.Transaction(amount=recurr_transaction.amount, target = recurr_transaction.target, transaction_type=recurr_transaction.type, date=next_date, id = recurr_transaction.id, category_id=recurr_transaction.category_id, recurr_transaction_id = recurr_transaction.id)
                        add_to_balance(recurr_transaction.amount, recurr_transaction.type)
                        create_notif(recurr_transaction.target, str(next_date), "Your recurring transaction has been completed",  'positive' if recurr_transaction.type == "Income" else 'negative')
                        old_date = next_date
                        next_date = next_date + datetime.timedelta(days=30)
                        recurr_transaction.next_date = next_date
                        db.session.add(new_record)
                        db.session.commit()
                        create_receipt(new_record.transaction_id, recurr_transaction.target, recurr_transaction.amount, recurr_transaction.type, str(old_date), recurr_transaction.category_id)

                    elif recurr_transaction.rate == "Yearly":
                        new_record = models.Transaction(amount=recurr_transaction.amount, target = recurr_transaction.target, transaction_type=recurr_transaction.type, date=next_date, id = recurr_transaction.id, category_id=recurr_transaction.category_id, recurr_transaction_id = recurr_transaction.id)
                        add_to_balance(recurr_transaction.amount, recurr_transaction.type)
                        create_notif(recurr_transaction.target, str(next_date), "Your recurring transaction has been completed",  'positive' if recurr_transaction.type == "Income" else 'negative')
                        next_date
                        next_date = next_date + datetime.timedelta(days=365)
                        recurr_transaction.next_date = next_date
                        db.session.add(new_record)
                        db.session.commit()
                        create_receipt(new_record.transaction_id, recurr_transaction.target, recurr_transaction.amount, recurr_transaction.type, str(old_date), recurr_transaction.category_id)

                

def get_regular_transactions():
        
    regular_transactions = models.Recurr_Transactions.query.filter_by(id=current_user.id).order_by(desc(models.Recurr_Transactions.start_date)).all()

    regular_tran_li = []

    for regular_tran in regular_transactions:
        regular_tran_li.append(
            {
                "target": regular_tran.target,
                "recurr_transactions_id": regular_tran.Recurr_Transactions_id,
                "amount": regular_tran.amount,
                'rate': regular_tran.rate,
                'category': Category.query.filter_by(category_id=regular_tran.category_id).first().name,
                'start_date': regular_tran.start_date,
                'next_date': regular_tran.next_date,
                'type': regular_tran.type,
                
            }
        )


    return regular_tran_li



def get_income_transactions_by_year_and_month(year, month):
    start_date = datetime.datetime(year, month, 1)
    end_date = datetime.datetime(year, month, 1).replace(month=month % 12 + 1 if month < 12 else 1, year=year + month // 12)
    total_amount = db.session.query(func.sum(Transaction.amount)).filter(Transaction.date >= start_date, Transaction.date < end_date, Transaction.id == current_user.id, Transaction.transaction_type == 'Income').scalar()
    
    return total_amount or 0

def get_expense_transactions_by_year_and_month(year, month):
    start_date = datetime.datetime(year, month, 1)
    end_date = datetime.datetime(year, month, 1).replace(month=month % 12 + 1 if month < 12 else 1, year=year + month // 12)
    total_amount = db.session.query(func.sum(Transaction.amount)).filter(Transaction.date >= start_date, Transaction.date < end_date, Transaction.id == current_user.id, Transaction.transaction_type == 'Expense').scalar()
    
    return total_amount or 0

def get_chart_data():
    current_date = datetime.datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    balance = get_user_balance()

    months = [(current_month - i) % 12 or 12 for i in range(9)] 
    
    years = [current_year - 1 if current_month - i <= 0 else current_year for i in range(9)]

    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    months_nine = [month_names[m - 1] for m in months]

    # Combine months and years
    labels = [f"{month} {year}" for month, year in zip(months_nine, years)]
    
    labels.reverse()
    months.reverse()
    years.reverse()
    income_list = []
    expense_list = []
    transfer_list = []
    
    for month, year in zip(months, years):
        
        total_income = get_income_transactions_by_year_and_month(year, month)
        

        income_list.append(total_income)

    for month, year in zip(months, years):

        total_income = get_expense_transactions_by_year_and_month(year, month)

        expense_list.append(total_income)

    if None in income_list:
        income_list = [0,0,0,0,0,0,0,0,0]
    if None in expense_list:
        expense_list = [0,0,0,0,0,0,0,0,0]
    if balance is None:
        balance.amount = 0
      
    
    transfer_list = [income_list[i] - expense_list[i] for i in range(len(income_list))]
    

    return labels, income_list, expense_list, transfer_list, balance.amount

def chart_data_bar() -> list:

    labels, income_list, expense_list, transfer_list, _ = get_chart_data()
    
    chart_data = [labels, income_list, expense_list, transfer_list]
    
    return chart_data

def chart_data_pie():
    _, income_list, expense_list, _, balance_amount = get_chart_data()

    expense_list = sum(expense_list)
    income_list = sum(income_list)

    pie_data = [income_list, expense_list, balance_amount]

    

    return pie_data



def get_currency_rates():
    today = date.today()
    rates = CurrencyRates().get_rates(['USDTRY', 'USDEUR', 'EURTRY', 'EURUSD', 'TRYEUR', 'TRYUSD'], today)
    return {f'{code1}{code2}': str(round(rate, 3)) for code1, code2, rate in rates}

def get_goal_categories():
    categories = Category.query.filter_by(id=current_user.id, type="goal").all()

    cat_li = []
    for category in categories:
        cat_li.append({
            'category_id': category.category_id,
            'name': category.name
        })

    return cat_li

def get_all_goals():
    goals = FinancialGoal.query.filter_by(id=current_user.id).order_by(asc(FinancialGoal.end_date)).all()
    current_date = datetime.datetime.now().date() 

    goal_li = []

    for goal in goals:
        goal_amount = goal.amount
        end_date = datetime.datetime.strptime(goal.end_date, '%Y-%m-%d').date()
        balance = Balance.query.filter_by(id=current_user.id, category='main').first()
        balance_amount = balance.amount
        progress = round((balance_amount / goal_amount) * 100, 2)
        time_left = (end_date - current_date).days
        amount_left = goal_amount - balance_amount if goal_amount - balance_amount > 0 else 0

        
        if goal.state == 'Expired':
            progress = goal.progress
            time_left = 0
            amount_left = goal.amount_left
        

        

        if time_left >= 0 and goal.state != 'Expired':
            if progress < 100 and goal.state != 'Expired':
                goal.progress= progress
                goal.time_left = time_left
                goal.amount_left = amount_left
                goal.state = 'Active'
            elif progress > 100:
                progress = 100
                goal.progress = progress
                goal.state = 'Completed'
                goal.time_left = time_left
                amount_left = 0
                goal.amount_left = amount_left
        elif time_left < 0 and goal.state != 'Expired':
            time_left = 0
            goal.time_left = time_left
            goal.state = 'Expired'
            progress = goal.progress
            amount_left = goal.amount_left
       

        
            

        

        goal_li.append({
            'goal_id': goal.financial_goal_id,
            'amount': goal.amount,
            'name': goal.name,
            'end_date': goal.end_date,
            'category': Category.query.filter_by(category_id=goal.category_id).first().name,
            'time_left': time_left,
            'progress':  progress,
            'balance_amount': balance_amount,
            'amount_left': amount_left,
            'goal_id': goal.financial_goal_id,
            'goal_state': goal.state


        })

        db.session.commit()
        
    return goal_li


def create_goal_notif():
    goals = FinancialGoal.query.filter_by(id=current_user.id).order_by(asc(FinancialGoal.end_date)).all()
    notifications_to_create = []
    
    for goal in goals:
        if goal.state == 'Active':
            goal.created_notif = False
        if not goal.created_notif:
            new_notif = None
            if goal.state == 'Completed':
                new_notif = Notification(
                    id=current_user.id,
                    state="new",
                    title="Congrats!",
                    description="A Goal has been completed.",
                    type="positive",
                    date = datetime.datetime.now().date()
                )
            elif goal.state == 'Inactive':
                new_notif = Notification(
                    id=current_user.id,
                    state="new",
                    title="Goal Expired",
                    description="A goal has expired.",
                    type="negative",
                    date = datetime.datetime.now().date()
                )
            
            if new_notif:
                notifications_to_create.append(new_notif)
                goal.created_notif = True
            else:
                pass
                
            
            
    db.session.add_all(notifications_to_create)
    db.session.commit()

def get_all_budgets():
    budgets = Budget.query.filter_by(id=current_user.id).order_by(asc(Budget.end_date)).all()
    current_date = datetime.datetime.now().date() 
    new_budgets_to_create = []
    budget_li = []


    for budget in budgets:

        budget_name = budget.name
        budget_amount = budget.amount
        budget_end_date = budget.end_date
        rate = budget.rate
        budget_category = Category.query.filter_by(category_id=budget.category_id).first().name
        budget_state = budget.state
        budget_time_left = budget.time_left
        budget_repeat = budget.repeat
        budget_amount_left = budget.amount_left
        budget_start_date = budget.start_date
        

        
        expense_sum = db.session.query(func.sum(Transaction.amount)).filter(Transaction.transaction_type=='Expense', Transaction.id==current_user.id, Transaction.date>=budget_start_date, Transaction.date<=budget_end_date, Transaction.category_id==budget.category_id).scalar()
        if not expense_sum:
            expense_sum = 0
        

        budget_progress = round((expense_sum / budget_amount) * 100, 2)
        budget_time_left = (budget_end_date - current_date).days
        budget_amount_left = budget_amount - expense_sum if budget_amount - expense_sum > 0 else 0

        if budget_progress >= 100 and budget_state != 'Exceeded Amount' and budget_time_left >= 0: 
            budget_progress = 100
            budget.progress = budget_progress
            budget.state = 'Exceeded Amount'
            budget_state = 'Exceeded Amount'
            budget.time_left = budget_time_left
            if budget_repeat == 'Yes':

                if budget.created_next_budget:
                    pass
                else:
                    budget.created_next_budget = True

                    if rate == 'Daily':
                        new_time_left = 1
                        add_to_current_date = datetime.timedelta(days=1)
                    elif rate == "Weekly":
                        new_time_left = 7
                        add_to_current_date = datetime.timedelta(days=7)
                    elif rate == "Monthly":
                        new_time_left = 30
                        add_to_current_date = datetime.timedelta(days=30)
                    elif rate == "Yearly":
                        new_time_left = 365
                        add_to_current_date = datetime.timedelta(days=365)
                    
                    new_start_date= budget_end_date
                    new_end_date = new_start_date + add_to_current_date
                    new_time_left = (new_end_date - current_date).days if (new_end_date - current_date).days > 0 else 0


                    new_budget = Budget(time_left = new_time_left, name=budget_name, amount=budget_amount, repeat= budget_repeat, 
                    state='Active', category_id=budget.category_id, rate=rate, id=current_user.id, end_date = new_end_date, start_date= new_start_date)
                    
                    new_budgets_to_create.append(new_budget)


        elif budget_progress < 100 and budget_time_left < 0 and budget_state != 'Inactive' and budget.state != 'Exceeded Amount':
            budget_time_left = 0
            budget.time_left = budget_time_left
            budget.state = 'Inactive'
            budget_state = 'Inactive'
            budget_progress = budget.progress
            if budget_repeat == 'Yes':

                if budget.created_next_budget:
                    pass
                else:
                    budget.created_next_budget = True

                    if rate == 'Daily':
                        new_time_left = 1
                        add_to_current_date = datetime.timedelta(days=1)
                    elif rate == "Weekly":
                        new_time_left = 7
                        add_to_current_date = datetime.timedelta(days=7)
                    elif rate == "Monthly":
                        new_time_left = 30
                        add_to_current_date = datetime.timedelta(days=30)
                    elif rate == "Yearly":
                        new_time_left = 365
                        add_to_current_date = datetime.timedelta(days=365)

                    new_start_date= budget_end_date
                    new_end_date = new_start_date + add_to_current_date
                    new_time_left = (new_end_date - current_date).days if (new_end_date - current_date).days > 0 else 0


                    new_budget = Budget(time_left = new_time_left, name=budget_name, amount=budget_amount, repeat= budget_repeat, 
                    state='Active', category_id=budget.category_id, rate=rate, id=current_user.id, end_date = new_end_date, start_date= new_start_date)
                    
                    new_budgets_to_create.append(new_budget)


        if budget_state == 'Active':
            budget.progress = budget_progress
            budget.time_left = budget_time_left
            budget.amount_left = budget_amount_left
        elif budget_state == 'Exceeded Amount':
            budget_progress = 100
            budget_amount_left = 0
            budget_time_left = budget.time_left
        elif budget_state == 'Inactive':
            budget_time_left = 0
            budget_progress= budget.progress
            budget_amount_left = budget.amount_left
                       
            

        
        budget_li.append({
            'budget_id': budget.budget_id,
            'budget_name': budget_name,
            'budget_amount': budget_amount,
            'budget_end_date': budget_end_date,
            'budget_category': budget_category,
            'budget_state': budget_state,
            'budget_time_left': budget_time_left,
            'budget_amount_spent': expense_sum,
            'budget_rate': rate,
            'budget_repeat': budget_repeat,
            'budget_amount_left': budget_amount_left,
            'budget_progress': budget_progress
        })

        db.session.commit()

    db.session.add_all(new_budgets_to_create)
    db.session.commit()

    for budget in new_budgets_to_create:
        budget_li.append({
            'budget_id': budget.budget_id,
            'budget_name': budget.name,
            'budget_amount': budget.amount,
            'budget_end_date': budget.end_date,
            'budget_category': budget.category.name,
            'budget_state': budget.state,
            'budget_time_left': budget.time_left,
            'budget_amount_spent': 0,
            'budget_rate': budget.rate,
            'budget_repeat': budget.repeat,
            'budget_amount_left': budget.amount_left,
            'budget_progress': 0
        })

    
    budget_li = sorted(budget_li, key=lambda x: x['budget_end_date'], reverse=True)
    
    return budget_li
    
    
def create_budget_notif():
    budgets = Budget.query.filter_by(id=current_user.id).order_by(asc(Budget.end_date)).all()
    notifications_to_create = []

    for budget in budgets:
        if not budget.created_notif:
            new_notif = None
        
            if budget.state == 'Exceeded Amount':
                new_notif = Notification(
                    id=current_user.id,
                    state="new",
                    title="Oops!",
                    description="A budget has exceeded its amount.",
                    type="positive",
                    date = datetime.datetime.now().date()
                )
            elif budget.state == 'Inactive':
                new_notif = Notification(
                    id=current_user.id,
                    state="new",
                    title="Budget Expired",
                    description="A budget has expired.",
                    type="negative",
                    date = datetime.datetime.now().date()
                )
            if new_notif:
                notifications_to_create.append(new_notif)
                budget.created_notif = True
            else:
                pass
            
    
    db.session.add_all(notifications_to_create)
    db.session.commit()

    


def create_receipt(transaction_id, target_name, amount, transaction_type, date, category):
    # Create the PDF
    pdf_filename = os.path.join(current_app.static_folder, 'receipts', f"{transaction_id}_receipt_{target_name}.pdf")
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter

    # Add the Wise Wallet title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(100, height - 50, "Wise Wallet")

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(100, height - 80, "Receipt") 

    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, height - 110, "Receipt Info") 
    c.drawString(300, height - 110, "To/From") 


    if os.path.exists('website\\static\\images\\logo.jpg'):
        c.drawImage(('website\\static\\images\\logo.jpg'), 450, height-100, width=200, height=100)  

    # Add transaction details
    c.setFont("Helvetica", 12)
    text_lines = [
        f"Type: {transaction_type}",
        f"Date: {date}",
        f"Category: {category}",
    ]

    y_position = height - 130
    for line in text_lines:
        c.drawString(100, y_position, line)
        y_position -= 20

    

    c.drawString(300, height-130, f"From: {current_user.first_name}")
    c.drawString(300, height-150, f"To: {target_name}")


    c.setFont("Helvetica-Bold", 15)
    c.drawString(100, height-220, f"TOTAL: ${amount}")
    c.line(100, height-230, 500, height-230)


    c.setFont("Helvetica-Oblique", 10)
    c.drawString(100, height-250, 'Thanks for using Wise Wallet!')

    

    # Add a footer
    c.setFont("Helvetica-Oblique", 10)
    footer_text = f"Generated by Wise Wallet on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    c.drawString(100, height-300, footer_text)

    # Save the PDF
    c.showPage()
    c.save()



    
    
    
    
    
    
