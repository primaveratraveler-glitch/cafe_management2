#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'cafe_management_secret_key'

# DB_NAME
DB_NAME = os.path.join(os.path.dirname(__file__), "cafe_management.db")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM ユーザー WHERE 名前 = ? AND パスワード = ?', (name, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['ユーザーID']
            session['user_name'] = user['名前']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='ユーザー名またはパスワードが正しくありません')
    
    return render_template('login.html')

# ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ダッシュボード（在庫一覧）
@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM カテゴリ ORDER BY カテゴリID').fetchall()
    products = conn.execute('''
        SELECT 商品.*, カテゴリ.カテゴリ名 
        FROM 商品 
        JOIN カテゴリ ON 商品.カテゴリID = カテゴリ.カテゴリID
        ORDER BY カテゴリ.カテゴリID, 商品.商品名
    ''').fetchall()
    conn.close()
    
    return render_template('dashboard.html', categories=categories, products=products, user_name=session.get('user_name'))

# 商品詳細
@app.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT 商品.*, カテゴリ.カテゴリ名 
        FROM 商品 
        JOIN カテゴリ ON 商品.カテゴリID = カテゴリ.カテゴリID
        WHERE 商品ID = ?
    ''', (product_id,)).fetchone()
    
    logs = conn.execute('''
        SELECT 入出庫ログ.*, ユーザー.名前 
        FROM 入出庫ログ 
        JOIN ユーザー ON 入出庫ログ.ユーザーID = ユーザー.ユーザーID
        WHERE 商品ID = ?
        ORDER BY 日時 DESC
    ''', (product_id,)).fetchall()
    
    conn.close()
    
    return render_template('product_detail.html', product=product, logs=logs)

# 入庫フォーム
@app.route('/add_stock/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add_stock(product_id):
    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        conn = get_db_connection()
        
        # 商品情報を取得
        product = conn.execute('SELECT * FROM 商品 WHERE 商品ID = ?', (product_id,)).fetchone()
        
        # 在庫を増やす
        conn.execute('UPDATE 商品 SET 在庫数 = 在庫数 + ? WHERE 商品ID = ?', (quantity, product_id))
        
        # ログに記録
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''
            INSERT INTO 入出庫ログ (商品ID, カテゴリID, 日時, ユーザーID, 数量)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, product['カテゴリID'], now, session['user_id'], quantity))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('product_detail', product_id=product_id))
    
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM 商品 WHERE 商品ID = ?', (product_id,)).fetchone()
    conn.close()
    
    return render_template('add_stock.html', product=product)

# 出庫フォーム
@app.route('/remove_stock/<int:product_id>', methods=['GET', 'POST'])
@login_required
def remove_stock(product_id):
    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        conn = get_db_connection()
        
        # 商品情報を取得
        product = conn.execute('SELECT * FROM 商品 WHERE 商品ID = ?', (product_id,)).fetchone()
        
        # 在庫を減らす
        conn.execute('UPDATE 商品 SET 在庫数 = 在庫数 - ? WHERE 商品ID = ?', (quantity, product_id))
        
        # ログに記録（マイナスで出庫を表現）
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''
            INSERT INTO 入出庫ログ (商品ID, カテゴリID, 日時, ユーザーID, 数量)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, product['カテゴリID'], now, session['user_id'], -quantity))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('product_detail', product_id=product_id))
    
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM 商品 WHERE 商品ID = ?', (product_id,)).fetchone()
    conn.close()
    
    return render_template('remove_stock.html', product=product)

# 入出庫ログ一覧
@app.route('/logs')
@login_required
def logs():
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT 入出庫ログ.*, 商品.商品名, カテゴリ.カテゴリ名, ユーザー.名前
        FROM 入出庫ログ
        JOIN 商品 ON 入出庫ログ.商品ID = 商品.商品ID
        JOIN カテゴリ ON 入出庫ログ.カテゴリID = カテゴリ.カテゴリID
        JOIN ユーザー ON 入出庫ログ.ユーザーID = ユーザー.ユーザーID
        ORDER BY 日時 DESC
    ''').fetchall()
    conn.close()
    
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
