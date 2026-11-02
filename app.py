import os
from dotenv import load_dotenv
import random
from flask import Flask,render_template,request,redirect,session
from database import connect_db
from werkzeug.security import generate_password_hash,check_password_hash

load_dotenv()

app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']

        db=connect_db()
        cursor=db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s",(email,))
        user=cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user['password'],password):
            session['user']=user['name']
            session['role']=user['role']
            return redirect('/dashboard')

        return "Invalid Email or Password"

    return render_template('login.html')

@app.route('/add_product',methods=['GET','POST'])
def add_product():
    if request.method=='POST':
        name=request.form['product_name']
        category=request.form['category']
        quantity=request.form['quantity']
        price=request.form['price']

        db=connect_db()
        cursor=db.cursor()
        sql="INSERT INTO products(product_name,category,quantity,price) VALUES(%s,%s,%s,%s)"
        cursor.execute(sql,(name,category,quantity,price))
        db.commit()
        cursor.close()
        db.close()

        return "Product Added Successfully!"

    return render_template('add_product.html')

@app.route('/products')
def products():
    db=connect_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    data=cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('products.html',products=data)

@app.route('/cart')
def cart():
    db=connect_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cart")
    data=cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('cart.html',cart=data)

@app.route('/add_to_cart/<int:product_id>',methods=['POST'])
def add_to_cart(product_id):
    db=connect_db()
    cursor=db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE id=%s",(product_id,))
    product=cursor.fetchone()

    if product and product['quantity']>0:
        cursor.execute(
            "INSERT INTO cart(product_id,product_name,price,quantity) VALUES(%s,%s,%s,%s)",
            (product['id'],product['product_name'],product['price'],1)
        )
        db.commit()

    cursor.close()
    db.close()
    return redirect('/cart')

@app.route('/place_order',methods=['POST'])
def place_order():
    db=connect_db()
    cursor=db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM cart")
    items=cursor.fetchall()

    for item in items:
        total=item['price']*item['quantity']
        cursor.execute(
            "INSERT INTO orders(product_name,price,quantity,total) VALUES(%s,%s,%s,%s)",
            (item['product_name'],item['price'],item['quantity'],total)
        )

    cursor.execute("DELETE FROM cart")
    db.commit()

    cursor.close()
    db.close()

    return redirect('/my_orders')

@app.route('/my_orders')
def my_orders():
    db=connect_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    data=cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('my_orders.html',orders=data)

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=generate_password_hash(request.form['password'])

        db=connect_db()
        cursor=db.cursor()
        cursor.execute(
            "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
            (name,email,password)
        )
        db.commit()
        cursor.close()
        db.close()
        return redirect('/login')

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html',name=session['user'])

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied! Admin Only"

    return render_template('admin_dashboard.html')

@app.route('/admin_orders')
def admin_orders():
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied! Admin Only"

    db=connect_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders=cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('admin_orders.html',orders=orders)

@app.route('/update_order/<int:order_id>',methods=['POST'])
def update_order(order_id):
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied! Admin Only"

    status=request.form['status']

    db=connect_db()
    cursor=db.cursor()
    cursor.execute(
        "UPDATE orders SET status=%s WHERE id=%s",
        (status,order_id)
    )
    db.commit()
    cursor.close()
    db.close()

    return redirect('/admin_orders')

@app.route('/revenue')
def revenue():
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied! Admin Only"

    db=connect_db()
    cursor=db.cursor(dictionary=True)

    cursor.execute("SELECT SUM(total) AS revenue FROM orders")
    data=cursor.fetchone()

    cursor.close()
    db.close()

    return render_template('revenue.html',revenue=data['revenue'] or 0)

@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect('/login')

@app.route('/profile',methods=['GET','POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')

    db=connect_db()
    cursor=db.cursor(dictionary=True)

    if request.method=='POST':
        name=request.form['name']
        cursor.execute("UPDATE users SET name=%s WHERE name=%s",(name,session['user']))
        db.commit()
        session['user']=name

    cursor.execute("SELECT * FROM users WHERE name=%s",(session['user'],))
    user=cursor.fetchone()

    cursor.close()
    db.close()

    return render_template('profile.html',user=user)

@app.route('/search')
def search():
    if 'user' not in session:
        return redirect('/login')

    keyword=request.args.get('keyword','')

    db=connect_db()
    cursor=db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM products WHERE product_name LIKE %s",
        ('%'+keyword+'%',)
    )

    products=cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('search.html',products=products,keyword=keyword)

@app.route('/feedback',methods=['GET','POST'])
def feedback():
    if 'user' not in session:
        return redirect('/login')

    if request.method=='POST':
        message=request.form['message']
        rating=request.form['rating']

        db=connect_db()
        cursor=db.cursor()

        cursor.execute(
            "INSERT INTO feedback(user_name,message,rating) VALUES(%s,%s,%s)",
            (session['user'],message,rating)
        )

        db.commit()
        cursor.close()
        db.close()

        return "Feedback Submitted Successfully!"

    return render_template('feedback.html')

@app.route('/grievance',methods=['GET','POST'])
def grievance():
    if 'user' not in session:
        return redirect('/login')

    if request.method=='POST':
        subject=request.form['subject']
        description=request.form['description']

        db=connect_db()
        cursor=db.cursor()

        cursor.execute(
            "INSERT INTO grievance(user_name,subject,description) VALUES(%s,%s,%s)",
            (session['user'],subject,description)
        )

        db.commit()
        cursor.close()
        db.close()

        return "Grievance Submitted Successfully!"

    return render_template('grievance.html')

@app.route('/employee_register',methods=['GET','POST'])
def employee_register():
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied! Admin Only"

    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        phone=request.form['phone']
        salary=request.form['salary']

        db=connect_db()
        cursor=db.cursor()
        cursor.execute(
            "INSERT INTO employees(name,email,phone,salary) VALUES(%s,%s,%s,%s)",
            (name,email,phone,salary)
        )
        db.commit()
        cursor.close()
        db.close()

        return "Employee Registered Successfully!"

    return render_template('employee_register.html')
@app.route('/contact',methods=['GET','POST'])
def contact():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        subject=request.form['subject']
        message=request.form['message']

        db=connect_db()
        cursor=db.cursor()
        cursor.execute(
            "INSERT INTO contact_messages(name,email,subject,message) VALUES(%s,%s,%s,%s)",
            (name,email,subject,message)
        )
        db.commit()
        cursor.close()
        db.close()

        return "Message Sent Successfully!"

    return render_template('contact.html')

@app.route('/stock')
def stock():
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied! Admin Only"

    db=connect_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products=cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('stock.html',products=products)

@app.route('/send_otp',methods=['POST'])
def send_otp():
    email=request.form['email']
    otp=str(random.randint(100000,999999))

    session['otp']=otp
    session['otp_email']=email

    return "Your Demo OTP is: "+otp

@app.route('/verify_otp',methods=['POST'])
def verify_otp():
    email=request.form['email']
    otp=request.form['otp']

    if email==session.get('otp_email') and otp==session.get('otp'):
        session.pop('otp',None)
        session.pop('otp_email',None)
        return "OTP Verified Successfully!"

    return "Invalid OTP!"

@app.route('/otp')
def otp_page():
    return render_template('otp.html')

@app.route('/salary_list')
def salary_list():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role')!='admin':
        return "Access Denied! Admin Only"

    db=connect_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees")
    employees=cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('salary_list.html',employees=employees)

@app.route('/attendance',methods=['GET','POST'])
def attendance():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role')!='admin':
        return "Access Denied! Admin Only"

    db=connect_db()
    cursor=db.cursor()

    if request.method=='POST':
        employee_id=request.form['employee_id']
        employee_name=request.form['employee_name']
        attendance_date=request.form['attendance_date']
        status=request.form['status']

        cursor.execute(
            "INSERT INTO employee_attendance(employee_id,employee_name,attendance_date,status) VALUES(%s,%s,%s,%s)",
            (employee_id,employee_name,attendance_date,status)
        )
        db.commit()

    cursor.close()
    db.close()
    return render_template('attendance.html')

@app.route('/salary_increment',methods=['GET','POST'])
def salary_increment():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role')!='admin':
        return "Access Denied! Admin Only"

    if request.method=='POST':
        employee_id=request.form['employee_id']
        employee_name=request.form['employee_name']
        old_salary=request.form['old_salary']
        new_salary=request.form['new_salary']
        increment_date=request.form['increment_date']

        db=connect_db()
        cursor=db.cursor()
        cursor.execute(
            "INSERT INTO salary_increment(employee_id,employee_name,old_salary,new_salary,increment_date) VALUES(%s,%s,%s,%s,%s)",
            (employee_id,employee_name,old_salary,new_salary,increment_date)
        )
        db.commit()
        cursor.close()
        db.close()

        return "Salary Increment Saved Successfully!"

    return render_template('salary_increment.html')

@app.route('/return_product',methods=['GET','POST'])
def return_product():
    if 'user' not in session:
        return redirect('/login')

    if request.method=='POST':
        order_id=request.form['order_id']
        product_name=request.form['product_name']
        customer_email=request.form['customer_email']
        reason=request.form['reason']
        return_date=request.form['return_date']

        db=connect_db()
        cursor=db.cursor()
        cursor.execute(
            "INSERT INTO product_returns(order_id,product_name,customer_email,reason,return_date) VALUES(%s,%s,%s,%s,%s)",
            (order_id,product_name,customer_email,reason,return_date)
        )
        db.commit()
        cursor.close()
        db.close()

        return "Return Request Submitted Successfully!"

    return render_template('return_product.html')

@app.route('/offers',methods=['GET','POST'])
def offers():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role')!='admin':
        return "Access Denied! Admin Only"

    db=connect_db()
    cursor=db.cursor()

    if request.method=='POST':
        offer_name=request.form['offer_name']
        description=request.form['description']
        discount=request.form['discount']
        start_date=request.form['start_date']
        end_date=request.form['end_date']

        cursor.execute(
            "INSERT INTO offers(offer_name,description,discount,start_date,end_date) VALUES(%s,%s,%s,%s,%s)",
            (offer_name,description,discount,start_date,end_date)
        )
        db.commit()

    cursor.close()
    db.close()
    return render_template('offers.html')

if __name__=='__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)