# Flask Web Application

from flask import Flask, render_template, jsonify
from pymongo import MongoClient

app = Flask(__name__)
