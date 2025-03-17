from flask import Flask, request, render_template, jsonify, send_file, redirect, session

app = Flask(__name__)

@app.route('/')
def base():
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True)
