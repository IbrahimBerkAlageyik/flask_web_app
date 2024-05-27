from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import re
import time
from flask import Blueprint, redirect, render_template, request, flash, jsonify, url_for, current_app
import flask
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from .defs import create_receipt, add_to_balance, chart_data_bar, create_budget_notif, create_goal_notif, create_user_categories, get_all_budgets, get_all_goals, get_all_transactions, get_goal_categories, get_last3_transactions, create_balance, chart_data_pie, get_currency_rates, get_new_notifs, get_old_notifs, get_regular_transactions, get_transaction_categories, recurr_check
import datetime
from .models import Balance, Budget, Category, Recurr_Transactions, User, Transaction, Notification, FinancialGoal, Message, Suggestions
from . import db
import json
from werkzeug.utils import secure_filename
from website import models
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
from .constants import HELP_LINKS_DESCRIPTION
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid




views = Blueprint('views', __name__)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
@views.route('/', methods=['GET'])
def home():
    return render_template("start.html", page="home")


@views.route('/admin', methods=['GET'])
@login_required
def admin():
    if request.method == 'POST':
        pass

    if current_user.email != "admin@gmail.com":
        return redirect(url_for('views.overview'))
    
    num_users = User.query.count() - 1 # -1 for admin 
    num_transactions = Transaction.query.count()
    num_budgets = Budget.query.count()
    num_goals = FinancialGoal.query.count()

    user_data = []
    if User.query.first() is None:
        user_data = []
    else:
        for user in User.query.all():
            if user.type == "admin":
                continue
            else:
                user_data.append({
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'password': user.password,
                    'transaction_count': Transaction.query.filter_by(id=user.id).count(),
                    'goal_count': FinancialGoal.query.filter_by(id=user.id).count(),
                    'budget_count': Budget.query.filter_by(id=user.id).count(),
                    'balance': Balance.query.filter_by(id=user.id, category='main').first().amount if Balance.query.filter_by(id=user.id, category='main').first() else 0,
                })
    

    suggestions_data = []
    if Suggestions.query.first() is None:
        suggestions_data = []
    else:
        for suggestion in Suggestions.query.all():
            suggestions_data.append({
                'id': suggestion.id,
                'title': suggestion.title,
                'description': suggestion.description,
                'image_url': suggestion.image_url,
                'link': suggestion.link
            })

    messages_data = []
    if Message.query.first() is None:
        messages_data = []
    else:
        for message in Message.query.order_by(desc(Message.date)).all():
            messages_data.append({
                'id': message.id,
                'sender_email': message.sender_email,
                'subject': message.subject,
                'body': message.body,
                'date': message.date
            })

    
    


    

    return render_template("admin.html", num_users = num_users, num_transactions= num_transactions, num_budgets= num_budgets,
                            num_goals=num_goals, user_data=user_data, suggestions_data=suggestions_data,
                              messages_data=messages_data)
@views.route('/sendRequest', methods=['POST'])
@login_required
def sendRequest():
    if flask.request.method == 'POST':
        subject = flask.request.form.get('subject')
        message = flask.request.form.get('message')
        sender = current_user.email

        if subject == '' or message == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.settings'))
        
        if len(subject) > 100:
            flash('Subject is too long!', category='error')
            return redirect(url_for('views.settings'))
        
        if len(message) > 1000:
            flash('Message is too long!', category='error')
            return redirect(url_for('views.settings'))
        

        today_messages = Message.query.filter_by(sender_email=current_user.email, date=datetime.datetime.now().date()).all()
        if len(today_messages) > 5:
            flash('You have exceeded the maximum number of requests for today.', category='error')
            return redirect(url_for('views.settings'))
        

        date = datetime.datetime.now().date()
        request = Message(subject=subject, body=message, sender_email=sender, date=date)
        db.session.add(request)
        db.session.commit()
        flash('Request sent!', category='success')
        
        return redirect(url_for('views.settings'))
    else:
        pass
def send_email(sender_email, sender_password, recipient_email, subject, body):
    # Set up the MIME
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject

    # Add body to email
    message.attach(MIMEText(body, 'plain'))

    # Log in to the SMTP server
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        
        # Send email
        server.send_message(message)

@views.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        email = request.form.get('profile-email')
        token = str(uuid.uuid4())
        expiration_time = int(time.time()) + 3600  # Expire in 1 hour
        

        if email == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.reset'))
        user = User.query.filter_by(email=email).first()
        if user:
            print(token)
            token = f"{token}-{expiration_time}"
            print(expiration_time)
            print(token)
            
            user.reset_token = token
            sender_email = ''
            sender_password = ''
            recipient_email = email
            subject = 'Reset your password. WiseWallet'
            body = f'Please follow the link to reset your password: http://localhost:5000/confirmReset/{token}'

            db.session.commit()
            

            send_email(sender_email, sender_password, recipient_email, subject, body)

    
        else:
            flash('User does not exist!', category='error')
            return redirect(url_for('views.reset')) 
        
    return render_template("reset.html", user = current_user, page="reset")

@views.route('/confirmReset/<token>', methods=['GET', 'POST'])
def confirm_reset(token):
    user = User.query.filter_by(reset_token=token).first()

    
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.reset'))
        user.password = generate_password_hash(password)
        db.session.commit()
        flash('Password changed!', category='success')
        return redirect(url_for('auth.login'))


    if token == None:
        flash('Invalid token!', category='error')
        return redirect(url_for('views.reset'))
    

    

    
    # Get the actual token and expiration time
    
    expiration_time = int(token.split('-')[-1])

    # Check if the token is expired
    if expiration_time < int(time.time()):
        flash('Token has expired!', category='error')
        return redirect(url_for('views.reset'))

    # Retrieve the user associated with the token
    if not user:
        flash('Invalid token!', category='error')
        return redirect(url_for('views.reset'))

    # Reset the user's password
    
    

    return render_template("confirmReset.html", user=current_user, token=token)



@views.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    if request.method == 'POST':
        current_date = datetime.datetime.now().date()
        amount = request.form.get('budget_amount')
        if amount == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.budget'))
        elif not amount.isnumeric():
            flash('Invalid amount!', category='error')
            return redirect(url_for('views.budget'))
        elif int(amount) <= 0:
            flash('Invalid amount!', category='error')
            return redirect(url_for('views.budget'))
        
        category = request.form.get('budget_category')
        if category == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.budget'))
        
        category_id = Category.query.filter_by(name=category).first().category_id
        rate = request.form.get('budget_rate')
        if rate == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.budget'))
        name = request.form.get('budget_name')
        if name == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.budget'))
        
        repeat = request.form.get('budget_repeat')
        if repeat == '':
            flash('Please fill in all fields!', category='error')
            return redirect(url_for('views.budget'))
        if rate == 'Daily':
            end_date =  current_date + datetime.timedelta(days=1)
        elif rate == "Weekly":
            end_date =  current_date + datetime.timedelta(days=7)
        elif rate == "Monthly":
            end_date =  current_date + datetime.timedelta(days=30)
        elif rate == "Yearly":
            end_date =  current_date + datetime.timedelta(days=365)

        time_left = (end_date - current_date).days
        

        new_budget = Budget(time_left = time_left, name=name, amount=amount, repeat= repeat, 
        state='Active', category_id=category_id, rate=rate, id=current_user.id, end_date = end_date, start_date = current_date)

        db.session.add(new_budget)
        db.session.commit()


    get_all_goals()
    create_goal_notif()
    budgets = get_all_budgets()
    create_budget_notif()
    categories = get_transaction_categories()
    new_notifs = get_new_notifs()
    old_notifs = get_old_notifs()

    for ext in ALLOWED_EXTENSIONS:
        image_path = os.path.join(current_app.static_folder, 'profile_pics', f'{current_user.id}.{ext}')
        if os.path.exists(image_path):
            profile_picture_url = url_for('static', filename=f'profile_pics/{current_user.id}.{ext}')
            break
    else:
        # If no image file found, use a default image
        profile_picture_url = url_for('static', filename='profile_pics/default.jpg')

    return render_template("budget.html", page="budget", user= current_user, categories=categories,
                           budgets = budgets, new_notifs = new_notifs, old_notifs = old_notifs,
                           profile_picture_url = profile_picture_url)

@views.route('/overview', methods=['GET', 'POST'])
@login_required
def overview():
    if request.method == 'POST':  # Do nothing if POST method is used
        pass

    
    goals =  get_all_goals()
    create_goal_notif()
    get_all_budgets()
    create_budget_notif()


    last_transactions = get_last3_transactions()
    
    new_notifs = get_new_notifs()
    old_notifs = get_old_notifs()
    bar_chart_data = chart_data_bar()
    pie_chart_data = chart_data_pie()
    balance  = Balance.query.filter_by(id=current_user.id, category='main').first()
    balance_amount = balance.amount

    suggestions = Suggestions.query.all()

    suggestions = []
    for suggest in suggestions:
        for suggest in suggestions:
            suggestions.append({
                'id': suggest.id,
                'title': suggest.title,
                'description': suggest.description,
                'image_url': suggest.image_url,
                'link': suggest.link
            })



    for ext in ALLOWED_EXTENSIONS:
        image_path = os.path.join(current_app.static_folder, 'profile_pics', f'{current_user.id}.{ext}')
        if os.path.exists(image_path):
            profile_picture_url = url_for('static', filename=f'profile_pics/{current_user.id}.{ext}')
            break
    else:
        # If no image file found, use a default image
        profile_picture_url = url_for('static', filename='profile_pics/default.jpg')
 

    return render_template("index.html", user=current_user, page="overview",
                           bar_chart_data = bar_chart_data, pie_chart_data = pie_chart_data, 
                           goals = goals, last_transactions=last_transactions, new_notifs = new_notifs, 
                           old_notifs = old_notifs, balance = balance_amount,
                           profile_picture_url = profile_picture_url
                           , suggestions= suggestions)  # Render the overview.html template with the appropriate variables


@views.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    if request.method == 'POST':
        if request.form.get('addtransaction_rate') == 'Once':
            destination = request.form.get('addtransaction_target')
            amount = request.form.get('addtransaction_amount')
            if int(amount) < 0:
                flash('Amount cannot be negative!', category='error')
                return redirect(url_for('views.transactions'))
            transaction_type = request.form.get('addtransaction_type')
            date_str = request.form.get('addtransaction_date') 

            current_date = datetime.datetime.now().date()
            if datetime.datetime.strptime(date_str, '%Y-%m-%d').date() > current_date:
                flash('Date cannot be in the future!', category='error')
                return redirect(url_for('views.transactions'))



            user_id = current_user.id
            category = request.form.get('addtransaction_category')
            if category == '':
                flash('Please select a category!', category='error')
                return redirect(url_for('views.transactions'))
            category_obj = Category.query.filter_by(name=category, id=user_id, type='transaction').first()
            category_id = category_obj.category_id

            new_transaction = Transaction(
            target=destination,
            amount=amount,
            transaction_type = transaction_type,
            date=date_str,
            id=user_id,
            category_id=category_id,
            )

            db.session.add(new_transaction)

            if transaction_type == 'Income':
                
                balance = Balance.query.filter_by(id=user_id).first()
                balance.amount += float(amount)
            else:
                balance = Balance.query.filter_by(id=user_id).first()
                balance.amount -= float(amount)

            



            db.session.commit()

            
            create_receipt(new_transaction.transaction_id, destination, amount, transaction_type, date_str, category_obj.name)




            flash('Transaction added!', category='success')
            return redirect(url_for('views.transactions'))
        
        else:
            target = request.form.get('addtransaction_target')
            amount = request.form.get('addtransaction_amount')

            if int(amount) < 0:
                flash('Amount cannot be negative!', category='error')
                return redirect(url_for('views.transactions'))
            
            transaction_type = request.form.get('addtransaction_type')
            if transaction_type == None or transaction_type == '':
                flash('Please select a transaction type!', category='error')
                return redirect(url_for('views.transactions'))
            date_str = request.form.get('addtransaction_date') # Get the date from the form
            date_obj = datetime.datetime.strptime(str(date_str), '%Y-%m-%d') # Parse the date string into a date object
            current_date = datetime.datetime.now().date()
            if datetime.datetime.strptime(date_str, '%Y-%m-%d').date() > current_date:
                flash('Date cannot be in the future!', category='error')
                return redirect(url_for('views.transactions'))

            user_id = current_user.id
            rate = request.form.get('addtransaction_rate')
            if rate ==  None or rate == '':
                flash('Please select a rate!', category='error')
                return redirect(url_for('views.transactions'))
            
            category = request.form.get('addtransaction_category')
            if category == '' or category == None:
                flash('Please select a category!', category='error')
                return redirect(url_for('views.transactions'))
            target_category = Category.query.filter_by(name=category, id=user_id, type='transaction').first()
            category_id = target_category.category_id


            

            new_recurr = Recurr_Transactions(
                target = target,
                amount = amount,
                type = transaction_type,
                start_date = date_obj,
                next_date = date_obj,
                id = user_id,
                category_id = category_id,
                rate = rate                
            )


            db.session.add(new_recurr)
            db.session.commit()
            

            flash('Transaction added!', category='success')
            return redirect(url_for('views.transactions'))
            


    recurr_check()
    get_all_goals()
    create_goal_notif()
    get_all_budgets()
    create_budget_notif()
    
    

    categories = get_transaction_categories()
    transactions = get_all_transactions()
    regular_transactions = get_regular_transactions()
    new_notifs = get_new_notifs()
    old_notifs = get_old_notifs()

    for ext in ALLOWED_EXTENSIONS:
        image_path = os.path.join(current_app.static_folder, 'profile_pics', f'{current_user.id}.{ext}')
        if os.path.exists(image_path):
            profile_picture_url = url_for('static', filename=f'profile_pics/{current_user.id}.{ext}')
            break
    else:
        # If no image file found, use a default image
        profile_picture_url = url_for('static', filename='profile_pics/default.jpg')

    return render_template("activity.html", user=current_user, page="transactions",
    categories = categories, transactions = transactions, regular_transactions = regular_transactions,
    new_notifs = new_notifs, old_notifs = old_notifs, profile_picture_url = profile_picture_url)

@views.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST': 
        first_name = request.form['userName']
        if first_name == '' or first_name ==  None:
            new_first_name = current_user.first_name
        else:
            if not re.match(r'^[a-zA-Z\s]+$', first_name):
                flash('Invalid first name!', category='error')
                return redirect(url_for('views.profile'))
            else:
                new_first_name = first_name
        
            
        email = request.form['userEmail']
        if email == '' or email == None:
            new_email = current_user.email
        else:
            if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
                flash('Invalid email!', category='error')
                return redirect(url_for('views.profile'))
            else:
                new_email = email
            
        
        picture = request.files['userImage']

        if picture is None:
            pass
        else:
            picture_name = picture.filename
            picture_name = secure_filename(picture_name)
            if '.' in picture_name:
                ext = picture_name.rsplit('.', 1)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    picture_extension = os.path.splitext(picture_name)[1]  
                    new_picture_name = str(current_user.id) + picture_extension
                    for extension in ['.png', '.jpg', '.jpeg']:
                        picture_name_to_delete = str(current_user.id) + extension
                        if os.path.isfile(os.path.join(current_app.static_folder, 'profile_pics', picture_name_to_delete)):
                            os.remove(os.path.join(current_app.static_folder, 'profile_pics', picture_name_to_delete))  # Delete the old picture

                    picture.save(os.path.join(current_app.static_folder, 'profile_pics', new_picture_name))

       
        
        user = User.query.filter_by(id=current_user.id).first()
        user.first_name = new_first_name
        user.email = new_email
        db.session.commit()
        flash('Profile updated!', category='success')
        return redirect(url_for('views.settings'))
        
    
    recurr_check()
    get_all_goals()
    create_goal_notif()
    get_all_budgets()
    create_budget_notif()
    new_notifs = get_new_notifs()
    old_notifs = get_old_notifs()

    for ext in ALLOWED_EXTENSIONS:
        image_path = os.path.join(current_app.static_folder, 'profile_pics', f'{current_user.id}.{ext}')
        if os.path.exists(image_path):
            profile_picture_url = url_for('static', filename=f'profile_pics/{current_user.id}.{ext}')
            break
    else:
        # If no image file found, use a default image
        profile_picture_url = url_for('static', filename='profile_pics/default.jpg')
    
    return render_template("settings.html", user=current_user, page="settings", new_notifs = new_notifs, old_notifs = old_notifs,
    main_categories = get_transaction_categories(), goal_categories = get_goal_categories(), 
    profile_picture_url = profile_picture_url)


@views.route('/profile', methods=['GET'])
@login_required
def profile():
    first_name = current_user.first_name
    email = current_user.email

    goal_categories = get_goal_categories()
    main_categories = get_transaction_categories()
    
    bar_chart_data = chart_data_bar()
    pie_chart_data = chart_data_pie()

    recurr_check()
    get_all_goals()
    create_goal_notif()
    get_all_budgets()
    create_budget_notif()
    new_notifs = get_new_notifs()
    old_notifs = get_old_notifs()

    for ext in ALLOWED_EXTENSIONS:
        image_path = os.path.join(current_app.static_folder, 'profile_pics', f'{current_user.id}.{ext}')
        if os.path.exists(image_path):
            profile_picture_url = url_for('static', filename=f'profile_pics/{current_user.id}.{ext}')
            break
    else:
        # If no image file found, use a default image
        profile_picture_url = url_for('static', filename='profile_pics/default.jpg')

    return render_template("profile.html", page="profile", user=current_user , bar_chart_data = bar_chart_data, pie_chart_data = pie_chart_data,
    profile_picture_url = profile_picture_url, first_name = first_name,
       email = email, goal_categories = goal_categories, main_categories = main_categories,
      new_notifs = new_notifs, old_notifs = old_notifs)



@views.route('/financialgoals', methods=['GET', 'POST'])
@login_required
def financialgoals():
    if request.method == 'POST': 
            current_date = datetime.datetime.now().date()

            user_goals = FinancialGoal.query.filter_by(id=current_user.id).all()
            if len(user_goals) >= 20:
                flash('You can only have 20 goals!', category='error')
                return redirect(url_for('views.financialgoals'))


            name = request.form.get('goal_name')
            if name == '':
                flash('Please fill in all fields!', category='error')
                return redirect(url_for('views.financialgoals'))
            end_date = request.form.get('goal_end_date')
            if end_date == '':
                flash('Please fill in all fields!', category='error')
                return redirect(url_for('views.financialgoals'))
            elif not re.match(r'^\d{4}-\d{2}-\d{2}$', end_date):
                flash('Invalid end date!', category='error')
                return redirect(url_for('views.financialgoals'))
            end_date_onj = datetime.datetime.strptime(end_date, '%Y-%m-%d')  # Parse the date string into a date object
            

            if end_date_onj.date() < current_date: # Check if the end date is < 
                flash('End date must be in the future!', category='error')
                return redirect(url_for('views.financialgoals'))
            else:


                amount = request.form.get('goal_amount') # Get the date from the form
                if amount == '':
                    flash('Please fill in all fields!', category='error')
                elif not amount.isnumeric():
                    flash('Invalid amount!', category='error')
                    return redirect(url_for('views.financialgoals'))
                elif int(amount) <= 0:
                    flash('Invalid amount!', category='error')
                    return redirect(url_for('views.financialgoals'))
                user_id = current_user.id
                category = request.form.get('goal_category')
                if category == '':
                    flash('Please fill in all fields!', category='error')
                    return redirect(url_for('views.financialgoals'))
                category_id = Category.query.filter_by(name=category).first().category_id

                new_transaction = FinancialGoal(
                name=name,
                amount=amount,
                end_date=end_date,
                category_id=category_id,
                id=user_id,
                state = "Active",
                progress = 0,
                amount_left = 0,
                time_left = 0
                )

                db.session.add(new_transaction)
                db.session.commit()

                flash('Goal added!', category='success')
                return redirect(url_for('views.financialgoals'))

    recurr_check()
    get_all_budgets()
    create_budget_notif()
    
    goal_categories = get_goal_categories()
    goals = get_all_goals()
    create_goal_notif()

    new_notifs = get_new_notifs()
    old_notifs = get_old_notifs()

    for ext in ALLOWED_EXTENSIONS:
        image_path = os.path.join(current_app.static_folder, 'profile_pics', f'{current_user.id}.{ext}')
        if os.path.exists(image_path):
            profile_picture_url = url_for('static', filename=f'profile_pics/{current_user.id}.{ext}')
            break
    else:
        # If no image file found, use a default image
        profile_picture_url = url_for('static', filename='profile_pics/default.jpg')

    return render_template("financialgoals.html",page="financialgoals", user=current_user,
    goal_categories = goal_categories, goals = goals, new_notifs = new_notifs, old_notifs = old_notifs,
    profile_picture_url = profile_picture_url)


@views.route('/update_notif_state', methods=['POST'])
@login_required
def update_notif_state():
    notifs = Notification.query.filter_by(id=current_user.id).all()
    data = request.get_json()

    state = data
    
    for notif in notifs:
        notif.state = state
    
    db.session.commit()
    
    return '', 204

@views.route('/delete-regular-transaction', methods=['POST'])
@login_required
def delete_regular_transaction():
    transaction_id = request.args.get('id')
    transaction = Recurr_Transactions.query.filter_by(Recurr_Transactions_id=transaction_id).first()
    db.session.delete(transaction)
    db.session.commit()
    return 'Successfully deleted regular transaction', 200

@views.route('/delete-transaction', methods=['POST'])
@login_required
def delete_transaction():
    print(request.args.get('id'))
    transaction_id = request.args.get('id')
    transaction = Transaction.query.filter_by(transaction_id =transaction_id).first()
    amount = transaction.amount
    type = transaction.transaction_type
    if type == "Income":
        add_to_balance(amount, "Expense")
    elif type == "Expense":
        add_to_balance(amount, "Income")
    db.session.delete(transaction)
    db.session.commit()


    pdfUrl = os.path.join(current_app.static_folder, 'receipts', f'{transaction.transaction_id}_receipt_{transaction.target}.pdf')
    if os.path.exists(pdfUrl):
        os.remove(pdfUrl)
    return 'Successfully deleted transaction', 200

@views.route('/delete-goal', methods=['POST'])
@login_required
def delete_goal():
    print(request.args.get('id'))
    goal_id = request.args.get('id')
    transaction = FinancialGoal.query.filter_by(financial_goal_id =goal_id).first()
    db.session.delete(transaction)
    db.session.commit()
    return 'Successfully deleted goal', 200

@views.route('/delete-budget', methods=['POST'])
@login_required
def delete_budget():
    print(request.args.get('id'))
    budget_id = request.args.get('id')
    budget = Budget.query.filter_by(budget_id = budget_id).first()
    db.session.delete(budget)
    db.session.commit()
    return 'Successfully deleted budget', 200


@views.route('/passwordChange', methods=['POST'])
@login_required
def passwordChange():
    if request.method == 'POST':
        old_password = request.form.get('currentPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')

        if old_password == '' or new_password == '' or confirm_password == '':
            flash('Please fill in all fields.', category='error')
            return redirect(url_for('views.settings'))

        
       

        if new_password != confirm_password:
            flash('Passwords do not match.', category='error')
            return redirect(url_for('views.settings'))

        elif not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{7,}$', new_password):
            flash('Password must contain at least one uppercase, one lowercase, and one digit with a minimum length of 7.', category='error')
            return redirect(url_for('views.settings'))

        else:
            if check_password_hash(current_user.password, old_password):
                current_user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password changed!', category='success')
                return redirect(url_for('views.settings'))

            else:
                flash('Incorrect password, try again.', category='error')
                return redirect(url_for('views.settings'))

    return redirect(url_for('views.settings'))

@views.route('/createCategory', methods=['POST'])
@login_required
def createCategory():
    if request.method == 'POST':


        name = request.form.get('category_name')
        if name == '':
            flash('Please fill in all fields.', category='error')
            return redirect(url_for('views.settings'))
        
        type = request.form.get('category_type')
        if type == '':
            flash('Please fill in all fields.', category='error')
            return redirect(url_for('views.settings'))
        if type == 'Main':
            type = 'transaction'
        type = type.lower()
        categories = Category.query.filter_by(id=current_user.id, type=type).all()
        if len(categories) >= 50:
            flash('You can only have 100 categories of this type.', category='error')
            return redirect(url_for('views.settings'))


        new_category = Category(name=name, type=type, id = current_user.id)
        db.session.add(new_category)
        db.session.commit()
        flash('Category added!', category='success')
        return redirect(url_for('views.settings'))
    
    return redirect(url_for('views.settings'))


@views.route('/delete-category', methods=['POST'])
@login_required
def delete_category():
    category_id = request.args.get('id')
    category = Category.query.filter_by(category_id=category_id, id = current_user.id).first()
    transactions = Transaction.query.filter_by(category_id=category_id, id = current_user.id).all()
    financial_goals = FinancialGoal.query.filter_by(category_id=category_id, id = current_user.id).all()
    if len(transactions) == 0 and len(financial_goals) == 0:
        db.session.delete(category)
        db.session.commit()
        return 'Deleted Category', 200
    else:
        return 'Can not delete Category if there are records associated with it', 400
    


@views.route('/startemail', methods=['POST'])
def startemail():
    if request.method == 'POST':
        name = request.form.get('emailName')
        phone = request.form.get('emailPhone')
        email = request.form.get('emailEmail')
        message = request.form.get('emailMessage')

        msg = f"Name: {name}\nPhone: {phone}\nEmail: {email} \n\n{message}"

        return 'Email sent!', 200
    
  
@views.route('/get-receipt', methods=['POST'])
def getReceipt():
    if request.method == 'POST':
        id = request.args.get('id')
        transaction = Transaction.query.filter_by(transaction_id = id).first()
        if transaction == None:
            return 'Transaction not found', 400
        file_name = f"{transaction.transaction_id}_receipt_{transaction.target}.pdf"
        receipt_url = url_for('static', filename=f'receipts/{file_name}')
        return receipt_url, 200
    

@views.route('/delete-user', methods=['POST'])
def deleteUser():
    if request.method == 'POST':
        id = request.args.get('id')
        
        user = User.query.filter_by(id = id).first()
        if user == None:
            return 'User not found', 400
        db.session.delete(user)
        db.session.commit()
        
        return 'Deleted User', 200
    
@views.route('/delete-suggestion', methods=['POST'])
def deleteSuggestion():
    if request.method == 'POST':
        id = request.args.get('id')
        
        suggestion = Suggestions.query.filter_by(id = id).first()
        if suggestion == None:
            return 'Suggestion not found', 400
        
        
                
        


        db.session.delete(suggestion)
        db.session.commit()
        
        return 'Deleted Suggestion', 200

@views.route('/addSuggestion', methods=['POST'])
def addSuggestion():
    if request.method == 'POST':
        name = request.form.get('title')
        link = request.form.get('link')
        description = request.form.get('description')
        picture = request.files['image']

        if picture is None:
            pass
        else:
            same_suggestion = Suggestions.query.filter_by(title=name, link=link).first()
            if same_suggestion is not None:
                flash('Suggestion already exists', category='error')
                return redirect(url_for('views.admin'))
            picture_name = picture.filename
            picture_name = secure_filename(picture_name)
            if '.' in picture_name:
                ext = picture_name.rsplit('.', 1)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    picture_extension = os.path.splitext(picture_name)[1]  
                    new_picture_name = str(name) + picture_extension
                    for extension in ['.png', '.jpg', '.jpeg']:
                        picture_name_to_delete = str(name) + extension
                        if os.path.isfile(os.path.join(current_app.static_folder, 'suggestionPics', picture_name_to_delete)):
                            os.remove(os.path.join(current_app.static_folder, 'suggestionPics', picture_name_to_delete))  # Delete the old picture

                    picture.save(os.path.join(current_app.static_folder, 'suggestionPics', new_picture_name))
                    suggestion = Suggestions(title=name, link=link, description=description, image_url=url_for('static', filename=f'suggestionPics/{new_picture_name}'))

        db.session.add(suggestion)
        db.session.commit()
        
        return redirect(url_for('views.admin'))
    






