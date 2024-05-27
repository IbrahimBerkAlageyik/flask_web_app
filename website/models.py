from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    password = db.Column(db.String(60), nullable=False)
    first_name = db.Column(db.String(20), nullable=True, default=None) #
    type = db.Column(db.String(20), nullable=False, default="client") 
    email = db.Column(db.String(120), nullable=False, unique=True) #
    state = db.Column(db.String(20), nullable=False, default="Active") #-
    reset_token = db.Column(db.String(120), nullable=True, default=None)

    categories = db.relationship('Category', backref='User', cascade='all, delete-orphan',  lazy=True)
    transactions = db.relationship('Transaction', backref='User', cascade='all, delete-orphan', lazy=True)
    notifications = db.relationship('Notification', backref='User', cascade='all, delete-orphan',  lazy=True)
    balances = db.relationship('Balance', backref='User', cascade='all, delete-orphan',  lazy=True)
    budgets = db.relationship('Budget', backref='User', cascade='all, delete-orphan',  lazy=True)
    recurr_transactions = db.relationship('Recurr_Transactions', backref='User', cascade='all, delete-orphan',  lazy=True)
    financialgoals = db.relationship('FinancialGoal', backref='User', cascade='all, delete-orphan',  lazy=True)


    
    
    def __repr__(self):
        return f"Account('{self.id}, {self.account_name}', '{self.income}', '{self.date_created}', '{self.state}', {self.type})"

class Notification(db.Model):
    notification_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(20), nullable=True, default="No Title")
    date = db.Column(db.Date, default=func.current_date())
    description = db.Column(db.String(250), nullable=True, default="No Description")
    type = db.Column(db.String(20), nullable=False, default="neutral") # positive negative neutral
    state = db.Column(db.String(10), nullable=False, default="new") #new or old



    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    
class Balance(db.Model):
    balance_id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=True, default = 0)
    category = db.Column(db.String(10), nullable=False) # main , goal


    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

   

    def __repr__(self):
        return f"Balance('{self.amount}', '{self.id}', '{self.category}')"


class Category(db.Model):
    category_id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False, default="transaction") # goal, transaction
    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    transactions = db.relationship('Transaction', backref='category', lazy=True)
    recurr_transactions = db.relationship('Recurr_Transactions', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True)

    financialgoals = db.relationship('FinancialGoal', backref='category', lazy=True)


    def __repr__(self):
        return f"Category('{self.name}')"
    


class Transaction(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(20), nullable=True, default=None)
    amount = db.Column(db.Float, nullable=True, default = 0)
    transaction_type = db.Column(db.String(10), nullable=False, default="Income") # income or expense
    date = db.Column(db.String(10), default=func.current_date())

    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)
    recurr_transaction_id = db.Column(db.Integer, db.ForeignKey('recurr__transactions.Recurr_Transactions_id'), nullable=True)
    

    def __repr__(self):
        return f"Transaction('{self.amount}', '{self.transaction_type}', '{self.date}', '{self.id}', '{self.category_id}', '{self.currency_id}')"


class Budget(db.Model):
    budget_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=True, default="No Name")
    end_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0)
    repeat = db.Column(db.String(10), nullable=False, default="No")
    rate = db.Column(db.String(10), nullable=False, default="Daily")
    state = db.Column(db.String(10), nullable=False, default="Active")
    progress = db.Column(db.Integer, nullable=False, default=0)
    amount_left = db.Column(db.Float, nullable=False, default=0)
    time_left = db.Column(db.Integer, nullable=True, default=None)
    created_notif = db.Column(db.Boolean, nullable=False, default=False)
    created_next_budget = db.Column(db.Boolean, nullable=False, default=False)
    start_date = db.Column(db.Date, nullable=False, default=func.current_date())



    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False) # need budget_categories table

    

    def __repr__(self):
        return f"Budget('{self.start_date}', '{self.end_date}', '{self.amount}', '{self.id}', '{self.category_id}', '{self.currency_id}')"

class FinancialGoal(db.Model):
    financial_goal_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=True, default="No Name")
    end_date = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    state = db.Column(db.String(10), nullable=False, default="Active")
    progress = db.Column(db.Integer, nullable=False, default=0)
    amount_left = db.Column(db.Float, nullable=False, default=0)
    time_left = db.Column(db.Integer, nullable=True, default=None)
    created_notif = db.Column(db.Boolean, nullable=False, default=False)


    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False) # need budget_categories table

    

class Recurr_Transactions(db.Model):
    Recurr_Transactions_id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(20), nullable=True, default=None)
    rate = db.Column(db.String(10), nullable=False) #  weekly  monthly  yearly
    start_date = db.Column(db.Date, nullable=False, default=func.current_date())
    next_date = db.Column(db.Date, nullable=False, default=func.current_date())
    type = db.Column(db.String(10), nullable=False, default="Income") #expense or income
    amount = db.Column(db.Float, nullable=False)
    id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)
    transactions = db.relationship('Transaction', backref='Recurr_Transactions', lazy=True)

    
    
    def __repr__(self):
        return f"Recurr_Transactions('{self.rate}', '{self.amount}', '{self.id}', '{self.currency_id}', '{self.category_id}')"


class Suggestions(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    link = db.Column(db.String(255))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), default="No Subject")
    date = db.Column(db.Date, default=func.current_date())
    body = db.Column(db.Text, nullable=False)


