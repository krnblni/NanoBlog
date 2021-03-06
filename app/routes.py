from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Post
from werkzeug.urls import url_parse
from datetime import datetime
from app.email import send_password_reset_email

@app.route("/", methods = ["GET", "POST"])
@app.route("/index", methods = ["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body = form.post.data, author = current_user)
        db.session.add(post)
        db.session.commit()
        flash("Congrats! Your post is now live.")
        return redirect(url_for("index"))
    page = request.args.get("page", 1, type = int)
    posts = current_user.followedPosts().paginate(page, app.config["POSTS_PER_PAGE"], False)
    nextUrl = url_for("index", page = posts.next_num) if posts.has_next else None
    prevUrl = url_for("index", page = posts.prev_num) if posts.has_prev else None
    return render_template("index.html",title = "Home", posts = posts.items, form = form, nextUrl = nextUrl, prevUrl = prevUrl)

@app.route("/login", methods = ["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = form.username.data).first()
        if user is None or not user.checkPassword(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember = form.rememberMe.data)
        nextPage = request.args.get("next")
        if not nextPage or url_parse(nextPage).netloc != "":
            return redirect(url_for("index"))
        return redirect(nextPage)
    return render_template("login.html", title = "Login", form = form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/register", methods = ["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username = form.username.data, email = form.email.data)
        user.setPassword(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations! Registration Completed.")
        return redirect(url_for("login"))
    return render_template("register.html", title = "Register", form = form)

@app.route("/user/<username>")
@login_required
def user(username):
    user = User.query.filter_by(username = username).first_or_404()
    page = request.args.get("page", 1, type = int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, app.config["POSTS_PER_PAGE"], False)
    nextUrl = url_for("user", username = user.username, page = posts.next_num) if posts.has_next else None
    prevUrl = url_for("user", username = user.username, page = posts.prev_num) if posts.has_prev else None
    return render_template("user.html", user = user, posts = posts.items, nextUrl = nextUrl, prevUrl = prevUrl)

@app.before_request
def beforeRequest():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@app.route("/edit_profile", methods = ["GET", "POST"])
@login_required
def editProfile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.aboutMe.data
        db.session.commit()
        flash("Your changes have been saved!")
        return redirect(url_for("editProfile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.aboutMe.data = current_user.about_me
    return render_template("edit_profile.html", title = "Edit Profile", form = form)

@app.route("/follow/<username>")
@login_required
def follow(username):
    user = User.query.filter_by(username = username).first()
    if user is None:
        flash("No user found with username '{}'".format(username))
        return redirect(url_for("index"))
    if user == current_user:
        flash("You cannot follow yourself!")
        return redirect(url_for("user", username = username))
    current_user.follow(user)
    db.session.commit()
    flash("Great! You are now following '{}'".format(username))
    return redirect(url_for("user", username = username))

@app.route("/unfollow/<username>")
@login_required
def unfollow(username):
    user = User.query.filter_by(username = username).first()
    if user is None:
        flash("No user found with username '{}'".format(username))
        return redirect(url_for("index"))
    if user == current_user:
        flash("You cannot unfollow yourself!")
        return redirect(url_for("user", username = username))
    current_user.unfollow(user)
    db.session.commit()
    flash("That's sad! You unfollowed '{}'".format(username))
    return redirect(url_for("user", username = username))

@app.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type = int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, app.config["POSTS_PER_PAGE"], False)
    nextUrl = url_for("explore", page = posts.next_num) if posts.has_next else None
    prevUrl = url_for("explore", page = posts.prev_num) if posts.has_prev else None
    return render_template("index.html", title = "Explore", posts = posts.items, nextUrl = nextUrl, prevUrl = prevUrl)

@app.route("/reset_password_request", methods = ["GET", "POST"])
def resetPasswordRequest():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash("Check your email for instructions to reset your password!")
        return redirect(url_for("login"))
    return render_template("reset_password_request.html", title = "Reset Password", form = form)

@app.route("/reset_password/<token>", methods = ["GET", "POST"])
def resetPassword(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verifyResetPasswordToken(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.setPassword(form.password.data)
        db.session.commit()
        flash("Your password has been updated.")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form = form)